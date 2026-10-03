"""三端通用 AI 智能助手 (ASM Copilot) API 路由
支持全端离线双模交互、会话审计与场景上下文感知
"""
from flask import Blueprint, request, jsonify, session
from models import db, AIChatLog
import copilot_engine

copilot_bp = Blueprint('copilot', __name__)


@copilot_bp.route('/api/copilot/chat', methods=['POST'])
def copilot_chat():
    """AI 智能助手交互接口"""
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    context_page = data.get('context_page', '/')

    if not message:
        return jsonify({
            'status': 'error',
            'reply': '请输入您想咨询的故障或售后问题。',
            'suggestions': [],
            'actions': []
        }), 400

    user_id = session.get('user_id')
    role = session.get('role', 'guest')

    history = data.get('history', [])

    result = copilot_engine.process_copilot_chat(
        user_prompt=message,
        role=role,
        context_page=context_page,
        user_id=user_id,
        db_session=db.session,
        history=history
    )

    return jsonify({
        'status': 'success',
        'reply': result['reply'],
        'intent': result['intent'],
        'suggestions': result['suggestions'],
        'actions': result['actions']
    })


@copilot_bp.route('/api/copilot/history', methods=['GET'])
def copilot_history():
    """获取当前用户最近对话记录"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'success', 'history': []})

    logs = AIChatLog.query.filter_by(user_id=user_id).order_by(AIChatLog.created_at.desc()).limit(10).all()
    history = [
        {
            'prompt': log.sanitized_prompt,
            'response': log.ai_response,
            'intent': log.intent_detected,
            'time': log.created_at.strftime('%H:%M')
        }
        for log in reversed(logs)
    ]
    return jsonify({'status': 'success', 'history': history})


@copilot_bp.route('/api/copilot/quick-dispatch', methods=['POST'])
def copilot_quick_dispatch():
    """AI 智能助手一键免填极速转单闭环接口"""
    data = request.get_json(silent=True) or {}
    description = (data.get('description') or '').strip()
    fault_name = (data.get('fault_name') or '家电综合故障').strip()
    phone = (data.get('phone') or '').strip()
    device_model = (data.get('device_model') or '通用智能家电').strip()
    priority = data.get('priority', 'normal')

    if not description:
        return jsonify({'status': 'error', 'message': '故障描述不可为空'}), 400

    from models import Customer, Device, WorkOrder, WorkOrderEvent, User
    from utils import utcnow
    import rules

    user_id = session.get('user_id')
    customer = None
    if user_id:
        user = User.query.get(user_id)
        if user and user.role == 'customer' and user.related_id:
            customer = Customer.query.get(user.related_id)

    if not customer:
        if phone:
            customer = Customer.query.filter_by(phone=phone).first()
            if not customer:
                customer = Customer(
                    name=f"快捷客户_{phone[-4:]}",
                    phone=phone,
                    address="待派工电话确认详细地址"
                )
                db.session.add(customer)
                db.session.flush()
        else:
            return jsonify({
                'status': 'need_phone',
                'message': '请提供联系手机号以便工程师上门联系'
            }), 200

    # 寻找或自动绑定设备
    device = Device.query.filter_by(customer_id=customer.id).first()
    if not device:
        from datetime import date
        device = Device(
            customer_id=customer.id,
            model=device_model,
            purchase_date=date.today(),
            warranty_months=12
        )
        db.session.add(device)
        db.session.flush()

    now = utcnow()
    warranty_flag, _ = rules.judge_warranty(device, now)
    order_no = rules.generate_order_no(now, db.session)

    order = WorkOrder(
        order_no=order_no,
        customer_id=customer.id,
        device_id=device.id,
        description=f"[AI极速报修] {fault_name}: {description}",
        priority=priority,
        status='PENDING',
        warranty_flag=warranty_flag,
        created_at=now
    )
    db.session.add(order)
    db.session.flush()

    event = WorkOrderEvent(
        order_id=order.id,
        from_status=None,
        to_status='PENDING',
        actor_role='customer',
        actor_name=customer.name,
        note='通过 Fastshot AI 智能助手极速一键报修成功，进入调度待派工池',
        created_at=now
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'order_no': order_no,
        'warranty_flag': warranty_flag,
        'warranty_text': '官方保修期内 (¥0.00)' if warranty_flag else '保外透明计价',
        'query_url': f'/query?order_no={order_no}',
        'message': f'🎉 恭喜！工单 {order_no} 已成功生成并推入调度中心，金牌技师将在 15 分钟内响应！'
    })


@copilot_bp.route('/api/copilot/extract-order', methods=['POST'])
def api_extract_order():
    """从自然语言中高精提取下单结构化要素"""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'status': 'error', 'message': '输入内容不可为空'}), 400

    extracted = copilot_engine.extract_order_copilot(text)
    return jsonify({
        'status': 'success',
        'extracted': extracted
    })

