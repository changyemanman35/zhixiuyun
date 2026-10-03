"""官方售后服务主界面路由 (Portal Blueprint)
融合苹果 (Apple Support) 与海尔 (Haier) 官方售后门户风格
提供：品牌服务大厅、常见故障排查、在线保修/延保查询与官方维修费用即时估算器
"""
from flask import Blueprint, render_template, request, jsonify, session
from models import db, Device, FaultType, Part, Customer, WorkOrder, ServiceStation, User, utcnow
import config
import rules

portal_bp = Blueprint('portal', __name__)


@portal_bp.route('/portal')
@portal_bp.route('/home')
def index():
    """官方售后服务门户主页"""
    fault_types = FaultType.query.filter_by(active=True).all()
    parts = Part.query.filter_by(active=True).all()
    stations = ServiceStation.query.filter_by(active=True).all()
    
    # 平台服务统计数据（展示真实透明度）
    total_orders = WorkOrder.query.count()
    closed_orders = WorkOrder.query.filter_by(status='CLOSED').count()
    
    return render_template(
        'portal.html',
        fault_types=fault_types,
        parts=parts,
        stations=stations,
        total_orders=total_orders,
        closed_orders=closed_orders,
        config=config
    )


@portal_bp.route('/stations')
def stations_list():
    """官方授权服务网点查询中心 (spec.md 2.3.0 F2)"""
    city = request.args.get('city', '').strip()
    query = ServiceStation.query.filter_by(active=True)
    if city:
        query = query.filter(ServiceStation.city.like(f"%{city}%"))
    stations = query.all()
    cities = db.session.query(ServiceStation.city).filter_by(active=True).distinct().all()
    city_list = [c[0] for c in cities if c[0]]
    return render_template('stations.html', stations=stations, city_list=city_list, current_city=city)


@portal_bp.route('/ai-assistant')
def ai_assistant():
    """AI 智能助手 — 分步跳转式引导极速报修与故障诊断"""
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    current_cust = None
    if user and user.role == 'customer':
        if user.related_id:
            current_cust = Customer.query.get(user.related_id)
        if not current_cust and user.phone:
            current_cust = Customer.query.filter_by(phone=user.phone).first()
        if not current_cust and session.get('customer_id'):
            current_cust = Customer.query.get(session.get('customer_id'))

    my_devices = current_cust.devices.all() if current_cust else []
    return render_template('ai_assistant.html', current_cust=current_cust, devices=my_devices)


@portal_bp.route('/safety')
@portal_bp.route('/compliance')
def safety_compliance():
    """平台安全合规、资金托管与双向隐私保护落地页"""
    return render_template('safety.html')


@portal_bp.route('/recruit')
@portal_bp.route('/join-tech')
def tech_recruit():
    """金牌师傅招募全景落地页（深度维修0抽成、出工排查费即时到账）"""
    return render_template('recruit.html')




@portal_bp.route('/portal/api/estimate', methods=['POST'])
def estimate_fee():
    """维修费用估算器 API（对应 Apple Support '费用是多少？'）"""
    data = request.get_json(silent=True) or {}
    part_id = data.get('part_id')
    warranty_type = data.get('warranty_type', 'out')  # 'in' 或 'out'
    
    visit_fee = config.VISIT_FEE_NORMAL
    labor_rate = config.LABOR_RATE_PER_HOUR
    labor_hours = 1.0  # 基础预计工时
    part_fee = 0.0
    part_name = "无需更换配件"
    
    if part_id and part_id != 'none':
        part = Part.query.get(part_id)
        if part:
            part_fee = float(part.unit_price)
            part_name = part.name
            
    labor_fee = labor_rate * labor_hours
    
    if warranty_type == 'in':
        # 保内全面免费
        return jsonify({
            'status': 'success',
            'warranty': True,
            'visit_fee': 0.0,
            'labor_fee': 0.0,
            'part_fee': 0.0,
            'total_fee': 0.0,
            'part_name': part_name,
            'tips': '在原厂保修期内且非人为损坏，上门费、工时费与配件费全免（¥0.00）。'
        })
    else:
        total_fee = visit_fee + labor_fee + part_fee
        return jsonify({
            'status': 'success',
            'warranty': False,
            'visit_fee': visit_fee,
            'labor_fee': labor_fee,
            'part_fee': part_fee,
            'total_fee': total_fee,
            'part_name': part_name,
            'tips': '保外维修费用严格按照官方公示标准收取，最终费用以工程师现场出具的诊断结果为准。'
        })


@portal_bp.route('/home-repair')
def home_repair():
    """民生便民家电维修专属落地页 (Warm Amber & Terracotta Approachable Style)"""
    parts = Part.query.filter_by(active=True).all()
    fault_types = FaultType.query.filter_by(active=True).all()
    stations = ServiceStation.query.filter_by(active=True).all()
    
    # 典型家电明码标价字典
    appliance_pricing = [
        {
            'category': '空调',
            'icon': '❄️',
            'desc': '挂机 / 柜机 / 中央空调',
            'services': [
                {'name': '空调上门深度清洗杀菌', 'price': '¥88 - ¥128', 'tag': '惠民特惠'},
                {'name': '变频空调加氟充注 (R410A/R32)', 'price': '¥120 - ¥180', 'tag': '明码实价'},
                {'name': '压缩机启动器 / 传感器更换', 'price': '¥150 - ¥240', 'tag': '原厂配件'},
                {'name': '内机漏水疏通与排水管更换', 'price': '¥60 - ¥90', 'tag': '当场修好'}
            ]
        },
        {
            'category': '洗衣机',
            'icon': '🌀',
            'desc': '滚筒 / 波轮 / 洗烘一体机',
            'services': [
                {'name': '免拆机高温蒸汽除菌清洗', 'price': '¥79 - ¥119', 'tag': '健康必选'},
                {'name': '排水泵 / 进水阀故障更换', 'price': '¥95 - ¥160', 'tag': '90天质保'},
                {'name': '皮带老化脱落 / 异响排查', 'price': '¥70 - ¥110', 'tag': '快速上门'},
                {'name': '电脑主控板芯片级检修', 'price': '¥160 - ¥260', 'tag': '官方认证'}
            ]
        },
        {
            'category': '冰箱冷柜',
            'icon': '🧊',
            'desc': '风冷无霜 / 双门 / 多门对开门',
            'services': [
                {'name': '温控器 / 化霜传感器更换', 'price': '¥90 - ¥150', 'tag': '原厂配件'},
                {'name': '冷藏室结冰漏水孔疏通', 'price': '¥50 - ¥80', 'tag': '半小时搞定'},
                {'name': '系统补氟与微漏打压检测', 'price': '¥140 - ¥220', 'tag': '环保冷媒'},
                {'name': '风机电机 / 启动继电器维修', 'price': '¥110 - ¥180', 'tag': '质保无忧'}
            ]
        },
        {
            'category': '厨卫电器',
            'icon': '🔥',
            'desc': '油烟机 / 燃气灶 / 电热水器',
            'services': [
                {'name': '强力吸油烟机拆洗除重油', 'price': '¥99 - ¥149', 'tag': '焕然一新'},
                {'name': '燃气灶点火针 / 脉冲点火器', 'price': '¥60 - ¥100', 'tag': '安全排查'},
                {'name': '电热水器深度除水垢镁棒更换', 'price': '¥89 - ¥139', 'tag': '省电净水'},
                {'name': '安全阀 / 混水阀漏水维修', 'price': '¥50 - ¥90', 'tag': '当场见效'}
            ]
        }
    ]
    
    return render_template(
        'home_repair.html',
        appliance_pricing=appliance_pricing,
        parts=parts,
        fault_types=fault_types,
        stations=stations,
        config=config
    )


@portal_bp.route('/api/home-repair/quick-book', methods=['POST'])
def quick_book():
    """便民家电 30 秒极速一键报修接口"""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    category = data.get('category', '').strip() or '智能家用电器'
    address = data.get('address', '').strip() or '用户常用家庭住址'
    desc = data.get('description', '').strip() or f'{category} 出现故障，申请快速上门检修'

    if not name or not phone:
        return jsonify({'status': 'error', 'message': '请填写联系人姓名与手机号码'}), 400

    # 1. 自动寻找或创建客户
    cust = Customer.query.filter_by(phone=phone).first()
    if not cust:
        cust = Customer(name=name, phone=phone, address=address)
        db.session.add(cust)
        db.session.flush()

    # 2. 自动寻找或创建该客户的名下设备
    from datetime import date
    device = Device.query.filter_by(customer_id=cust.id, model=category).first()
    if not device:
        import random
        device = Device(
            customer_id=cust.id,
            model=category,
            serial_no=f"HOME-{category[:2]}-{phone[-4:]}-{random.randint(100, 999)}",
            purchase_date=date.today()
        )
        db.session.add(device)
        db.session.flush()

    # 3. 判定保修与生成统一工单
    warranty_flag = False
    now = utcnow()
    order_no = rules.generate_order_no(now, db.session)

    from models import WorkOrderEvent
    order = WorkOrder(
        order_no=order_no,
        customer_id=cust.id,
        device_id=device.id,
        description=f"【便民家电预约】{category}：{desc}（地址：{address}）",
        priority='urgent',
        warranty_flag=warranty_flag,
        status='PENDING'
    )
    db.session.add(order)
    db.session.flush()

    # 4. 写入创建事件
    ev = WorkOrderEvent(
        work_order_id=order.id,
        from_status=None,
        to_status='PENDING',
        actor_role='customer',
        note='便民家电落地页一键快捷报修'
    )
    db.session.add(ev)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'order_no': order_no,
        'message': f'预约成功！工单号 {order_no}，工程师将在 15 分钟内与您电话确认上门时间！'
    })

