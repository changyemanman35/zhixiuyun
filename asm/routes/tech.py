from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, WorkOrder, Technician, FaultType, Part, OrderPart
from routes.auth import roles_required
import rules
import state_machine
import config

bp = Blueprint('tech', __name__)

def get_current_tech_id():
    tech_id = session.get('current_tech_id')
    if not tech_id:
        first_tech = Technician.query.filter_by(active=True).first()
        if first_tech:
            tech_id = first_tech.id
            session['current_tech_id'] = tech_id
    return tech_id

@bp.route('/tech', methods=['GET'])
@roles_required('technician', 'dispatcher')
def tech_index():
    tech_id = get_current_tech_id()
    current_tech = Technician.query.get(tech_id) if tech_id else None
    techs = Technician.query.filter_by(active=True).all()
    orders_by_status = {}
    if tech_id:
        orders = WorkOrder.query.filter_by(technician_id=tech_id).all()
        for order in orders:
            orders_by_status.setdefault(order.status, []).append(order)
            
    # 3.0 C2C: 查询附近等待师傅抢单的已预付工单池 (PENDING 且未分配技师)
    pool_orders = WorkOrder.query.filter(
        WorkOrder.technician_id == None,
        WorkOrder.status.in_(['PENDING', 'ASSIGNED'])
    ).order_by(WorkOrder.created_at.desc()).limit(10).all()

    return render_template(
        'tech.html',
        current_tech_id=tech_id,
        current_tech=current_tech,
        techs=techs,
        orders_by_status=orders_by_status,
        pool_orders=pool_orders
    )

@bp.route('/tech/switch', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_switch():
    tech_id = request.form.get('tech_id')
    if tech_id:
        session['current_tech_id'] = int(tech_id)
        flash('技师切换成功', 'success')
    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/grab', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_grab(oid):
    """3.0 C2C: 维修师极速抢单"""
    tech_id = get_current_tech_id()
    if not tech_id:
        flash('未找到当前有效技师身份', 'danger')
        return redirect(url_for('tech.tech_index'))

    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id:
        flash('该单已被其他师傅抢先一步接走啦！', 'warning')
        return redirect(url_for('tech.tech_index'))

    from models import utcnow
    order.technician_id = tech_id
    order.status = 'ASSIGNED'
    order.dispatched_at = utcnow()

    from models import WorkOrderEvent
    event = WorkOrderEvent(
        work_order_id=order.id,
        from_status='PENDING',
        to_status='ASSIGNED',
        actor_role='technician',
        actor_id=tech_id,
        note='附近维修师在邻里大厅一键抢单成功，准备上门服务',
        created_at=utcnow()
    )
    db.session.add(event)
    try:
        db.session.commit()
        flash(f'🎉 抢单成功！请尽快与客户联系，并上门输入客户的现场核销码打卡！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('抢单失败: ' + str(e), 'danger')

    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/checkin', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_checkin(oid):
    """3.0 C2C: 师傅到场输入 6 位核销码打卡，解冻上门费至师傅钱包"""
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id != tech_id:
        flash('只能核销自己的接单', 'danger')
        return redirect(url_for('tech.tech_index'))

    code = (request.form.get('checkin_code') or '').strip().upper()
    if not code or (order.checkin_code and code != order.checkin_code.upper()):
        flash('核销码错误！请向客户索取手机上展示的 6 位动态验证码', 'danger')
        return redirect(url_for('tech.tech_index'))

    from models import utcnow
    order.checkin_at = utcnow()
    order.pay_status = 'SETTLED'
    
    # 扣除平台佣金后结算给师傅
    net_visit_fee = max(0.0, (order.visit_fee or 30.0) - (order.platform_commission or 5.0))
    tech = Technician.query.get(tech_id)
    if tech:
        tech.balance = (tech.balance or 0.0) + net_visit_fee

    try:
        state_machine.transition(order, 'IN_PROGRESS', actor_role='technician', actor_id=tech_id, note=f'现场核销码 {code} 校验通过，上门费 ¥{net_visit_fee:.2f} 已划拨至技师钱包，开始现场检修')
        db.session.commit()
        flash(f'✅ 现场核销成功！扣除平台服务费后，¥{net_visit_fee:.2f} 已到账您的钱包余额，请开始现场排查与线下协商！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('核销处理失败: ' + str(e), 'danger')

    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/offline-finish', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_offline_finish(oid):
    """3.0 C2C: 线下检修完成终态归档"""
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id != tech_id:
        flash('只能操作自己的接单', 'danger')
        return redirect(url_for('tech.tech_index'))

    result_type = request.form.get('result_type', 'fixed')
    note = (request.form.get('note') or '').strip()

    from models import utcnow
    if result_type == 'fixed':
        order.offline_status = 'FIXED_OFFLINE'
        order.resolution_note = f"[现场已维修] {note}"
    else:
        order.offline_status = 'ABORTED_OFFLINE'
        order.resolution_note = f"[客户放弃维修] {note} (基础排查已完成)"

    order.completed_at = utcnow()

    # 跃迁至 WAIT_CONFIRM，交由客户验收打分与最终闭环
    try:
        state_machine.transition(order, 'WAIT_CONFIRM', actor_role='technician', actor_id=tech_id, note=f'现场服务结束: {order.resolution_note}，待客户确认打分')
        db.session.commit()
        flash('现场服务已提交！工单已转交客户确认验收并评分。', 'success')
    except Exception as e:
        order.status = 'WAIT_CONFIRM'
        from models import WorkOrderEvent
        event = WorkOrderEvent(
            work_order_id=order.id,
            from_status='IN_PROGRESS',
            to_status='WAIT_CONFIRM',
            actor_role='technician',
            actor_id=tech_id,
            note=f'现场服务已完结: {order.resolution_note}，待客户验收打分',
            created_at=utcnow()
        )
        db.session.add(event)
        db.session.commit()
        flash('现场服务已提交，等待客户验收评分', 'success')

    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/start', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_start(oid):
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id != tech_id:
        flash('只能操作自己的工单', 'danger')
        return redirect(url_for('tech.tech_index'))
    try:
        state_machine.transition(order, 'IN_PROGRESS', actor_role='technician', actor_id=tech_id)
        db.session.commit()
        flash('工单已开工', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/hold', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_hold(oid):
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    note = request.form.get('note')
    if order.technician_id != tech_id:
        flash('只能操作自己的工单', 'danger')
        return redirect(url_for('tech.tech_index'))
    try:
        state_machine.transition(order, 'ON_HOLD', actor_role='technician', actor_id=tech_id, note=note)
        db.session.commit()
        flash('工单已挂起', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/resume', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_resume(oid):
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id != tech_id:
        flash('只能操作自己的工单', 'danger')
        return redirect(url_for('tech.tech_index'))
    try:
        state_machine.transition(order, 'IN_PROGRESS', actor_role='technician', actor_id=tech_id)
        db.session.commit()
        flash('工单已恢复', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
    return redirect(url_for('tech.tech_index'))

@bp.route('/tech/<int:oid>/complete', methods=['GET'])
@roles_required('technician', 'dispatcher')
def tech_complete_form(oid):
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    if order.technician_id != tech_id:
        flash('只能操作自己的工单', 'danger')
        return redirect(url_for('tech.tech_index'))
        
    fault_types = FaultType.query.filter_by(active=True).all()
    parts = Part.query.filter_by(active=True).all()
    labor_hours_prefill = rules.prefill_labor_hours(order)
    
    return render_template('complete_form.html', order=order, fault_types=fault_types, parts=parts,
                           resolutions=config.RESOLUTIONS, labor_hours_prefill=labor_hours_prefill)

@bp.route('/tech/<int:oid>/complete', methods=['POST'])
@roles_required('technician', 'dispatcher')
def tech_complete_submit(oid):
    tech_id = get_current_tech_id()
    order = WorkOrder.query.get_or_404(oid)
    
    if order.technician_id != tech_id:
        flash('只能操作自己的工单', 'danger')
        return redirect(url_for('tech.tech_index'))
        
    fault_type_id = request.form.get('fault_type_id')
    resolution = request.form.get('resolution')
    resolution_note = request.form.get('resolution_note')
    try:
        labor_hours = float(request.form.get('labor_hours', 0))
    except ValueError:
        flash('工时格式错误', 'danger')
        return redirect(url_for('tech.tech_complete_form', oid=oid))
        
    if not (0.5 <= labor_hours <= 24):
        flash('工时必须在 0.5 到 24 之间', 'danger')
        return redirect(url_for('tech.tech_complete_form', oid=oid))
        
    if not fault_type_id or not resolution:
        flash('故障类型和处理方式为必填项', 'danger')
        return redirect(url_for('tech.tech_complete_form', oid=oid))

    parts_detail = []
    order_parts_to_add = []
    parts_to_deduct = []

    for key, value in request.form.items():
        if key.startswith('qty_'):
            try:
                qty = int(value)
                if qty > 0:
                    part_id = int(key.replace('qty_', ''))
                    part = Part.query.get(part_id)
                    if part:
                        # 检查库存防超卖守卫 (spec.md 2.3.0 F4)
                        if part.stock_quantity < qty:
                            flash(f'配件【{part.name}】库存不足 (当前可用: {part.stock_quantity}, 需求: {qty})，请联系调度备料！', 'danger')
                            return redirect(url_for('tech.tech_complete_form', oid=oid))
                        
                        old_sn = request.form.get(f'old_sn_{part_id}', '').strip()
                        parts_detail.append((part.unit_price, qty))
                        parts_to_deduct.append((part, qty))
                        order_parts_to_add.append(OrderPart(
                            order_id=order.id,
                            part_id=part.id,
                            quantity=qty,
                            unit_price=part.unit_price,
                            old_part_sn=old_sn if old_sn else None,
                            old_part_returned=False
                        ))
            except ValueError:
                continue

    try:
        # Calculate fee
        fee_result = rules.calc_fee(order, parts_detail=parts_detail, labor_hours=labor_hours)
        
        # State transition
        state_machine.transition(order, 'WAIT_CONFIRM', actor_role='technician', actor_id=tech_id)
        
        # Write parts and atomic deduct stock
        for part_obj, deduct_qty in parts_to_deduct:
            part_obj.stock_quantity -= deduct_qty
            
        for op in order_parts_to_add:
            db.session.add(op)
            
        order.fault_type_id = int(fault_type_id)
        order.resolution = resolution
        order.resolution_note = resolution_note
        order.labor_hours = labor_hours
        
        order.labor_fee = fee_result['labor_fee']
        order.part_fee = fee_result['part_fee']
        order.visit_fee = fee_result['visit_fee']
        order.total_fee = fee_result['total_fee']
        
        db.session.commit()
        flash('工单已完工提交，备件库存已自动核减', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('tech.tech_complete_form', oid=oid))
        
    return redirect(url_for('tech.tech_index'))
