from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import timedelta
from models import db, WorkOrder, WorkOrderEvent, Customer, Device, Technician, utcnow
from routes.auth import roles_required
import rules
import state_machine
import traceback

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/')
@roles_required('dispatcher')
def board():
    # 查询所有非终态工单，按状态分组
    orders = WorkOrder.query.filter(WorkOrder.status.notin_(['CLOSED', 'CANCELLED'])).all()
    
    groups = {
        'PENDING': [],
        'ASSIGNED': [],
        'IN_PROGRESS': [],
        'ON_HOLD': [],
        'WAIT_CONFIRM': []
    }
    
    now = utcnow()
    for o in orders:
        if o.status in groups:
            # 计算预警级别
            o.sla_level = rules.sla_level(o)
            
            # 计算停留时长
            last_event = WorkOrderEvent.query.filter_by(work_order_id=o.id, to_status=o.status).order_by(WorkOrderEvent.created_at.desc()).first()
            if last_event:
                stay_time = now - last_event.created_at
            else:
                stay_time = now - o.created_at
            
            # 格式化时长
            total_seconds = int(stay_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            o.stay_time_str = f"{hours}h {minutes}m"
            o.is_rework_30d = rules.is_rework_30d(o, db.session)
            
            groups[o.status].append(o)

    active_techs = Technician.query.filter_by(active=True).all()
    # 为 PENDING 工单注入推荐技师
    for p_order in groups['PENDING']:
        recs = rules.recommend_technician(p_order, active_techs, db.session)
        p_order.recommended_tech = recs[0] if recs else None
            
    return render_template('board.html', groups=groups, orders=orders, active_techs=active_techs)

from routes.auth import roles_required, login_required
from flask import session
from models import db, WorkOrder, WorkOrderEvent, Customer, Device, Technician, User, utcnow

@orders_bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
@roles_required('customer', 'dispatcher')
def new_order():
    current_role = session.get('role', 'customer')
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    
    current_cust = None
    if current_role == 'customer':
        if user and user.related_id:
            current_cust = Customer.query.get(user.related_id)
        if not current_cust and user and user.phone:
            current_cust = Customer.query.filter_by(phone=user.phone).first()
        if not current_cust and session.get('customer_id'):
            current_cust = Customer.query.get(session.get('customer_id'))

    is_customer_mode = (current_role == 'customer' and current_cust is not None)

    active_techs = Technician.query.filter_by(active=True).all()

    if request.method == 'GET':
        if is_customer_mode:
            my_devices = current_cust.devices.all() if current_cust else []
            return render_template('order_new.html', is_customer=True, current_cust=current_cust, devices=my_devices, active_techs=active_techs)
        else:
            customers = Customer.query.all()
            return render_template('order_new.html', is_customer=False, customers=customers, active_techs=active_techs)
        
    if is_customer_mode and not request.form.get('customer_id'):
        customer_id = current_cust.id
    else:
        customer_id = request.form.get('customer_id') or (current_cust.id if current_cust else None)

    # 若尚未关联客户但提交了联系方式（如AI助手分步报修），自动匹配或建档
    if not customer_id and request.form.get('contact_phone'):
        c_phone = request.form.get('contact_phone', '').strip()
        c_name = request.form.get('contact_name', '').strip() or '在线客户'
        c_addr = request.form.get('service_address', '').strip()
        if c_phone:
            matched_cust = Customer.query.filter_by(phone=c_phone).first()
            if not matched_cust:
                matched_cust = Customer(name=c_name, phone=c_phone, address=c_addr or '服务地址待上门确认')
                db.session.add(matched_cust)
                db.session.flush()
            customer_id = matched_cust.id
            if user and not user.related_id:
                user.related_id = customer_id

    device_id = request.form.get('device_id')
    new_device_model = request.form.get('new_device_model', '').strip()
    description = request.form.get('description', '').strip()
    if not description:
        description = '待师傅上门现场排查检测（客户一键报修）'
    priority = request.form.get('priority', 'normal')

    # 支持客户在确认地址与电话时直接更新默认信息
    custom_addr = request.form.get('service_address', '').strip()
    if current_cust and custom_addr and current_cust.address != custom_addr:
        current_cust.address = custom_addr
    custom_phone = request.form.get('contact_phone', '').strip()
    if current_cust and custom_phone and current_cust.phone != custom_phone:
        current_cust.phone = custom_phone

    # 现场登记自购新设备支持 (零设备客户平滑建档)
    if (not device_id or device_id == 'new') and new_device_model:
        from datetime import date
        new_sn = request.form.get('new_device_sn', '').strip()
        device = Device(
            customer_id=customer_id,
            model=new_device_model,
            serial_no=new_sn if new_sn else None,
            purchase_date=date.today(),
            warranty_months=12
        )
        db.session.add(device)
        db.session.flush()
        device_id = device.id
    else:
        device = Device.query.get(device_id) if device_id else None
    
    if not customer_id or not device_id or not description:
        flash('请填写完整必填信息（选择/登记设备及故障描述）', 'danger')
        return redirect(url_for('orders.new_order'))
        
    if not device:
        flash('设备档案不存在', 'danger')
        return redirect(url_for('orders.new_order'))
        
    # B-4: 同一设备30天内二次报修时flash提示
    now = utcnow()
    thirty_days_ago = now - timedelta(days=30)
    recent_order = WorkOrder.query.filter(
        WorkOrder.device_id == device_id,
        WorkOrder.created_at >= thirty_days_ago
    ).first()
    if recent_order:
        flash('该设备在30天内有过报修记录', 'warning')
        
    now = utcnow()
    warranty_flag, _ = rules.judge_warranty(device, now)
    order_no = rules.generate_order_no(now, db.session)
    
    app_date_str = request.form.get('appointment_date')
    app_slot = request.form.get('appointment_slot')
    app_date = None
    if app_date_str:
        try:
            from datetime import date
            app_date = date.fromisoformat(app_date_str)
        except Exception:
            pass

    import secrets
    checkin_code = secrets.token_hex(3).upper()

    selected_tech_id = request.form.get('selected_tech_id')
    assigned_tech = None
    if selected_tech_id and selected_tech_id != 'broadcast':
        try:
            assigned_tech = Technician.query.get(int(selected_tech_id))
        except Exception:
            assigned_tech = None

    final_status = 'ASSIGNED' if assigned_tech else 'PENDING'
    dispatched_time = now if assigned_tech else None

    order = WorkOrder(
        order_no=order_no,
        customer_id=customer_id,
        device_id=device_id,
        technician_id=assigned_tech.id if assigned_tech else None,
        category=device.model if device else '家用电器',
        description=description,
        priority=priority,
        warranty_flag=warranty_flag,
        appointment_date=app_date,
        appointment_slot=app_slot,
        status=final_status,
        dispatched_at=dispatched_time,
        visit_fee=30.0,
        platform_commission=5.0,
        pay_status='PAID',
        checkin_code=checkin_code,
        created_at=now
    )
    db.session.add(order)
    db.session.flush() # get order.id
    
    note_msg = f'客户在线预付上门费 ¥30.00 (平台托管)，生成现场核销码【{checkin_code}】'
    if assigned_tech:
        note_msg += f'，客户已指定附近专修师傅【{assigned_tech.name}】上门'
    else:
        note_msg += '，已向附近 5 公里匹配师傅广播派单'

    event = WorkOrderEvent(
        work_order_id=order.id,
        from_status=None,
        to_status=final_status,
        actor_role='customer' if is_customer_mode else 'dispatcher',
        note=note_msg,
        created_at=now
    )
    db.session.add(event)
    
    try:
        db.session.commit()
        
        # 兼容滴滴打车式原地沉浸履约的异步 Fetch / AJAX 请求
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('format') == 'json' or request.form.get('is_ajax') == '1':
            return {
                'success': True,
                'order_id': order.id,
                'order_no': order.order_no,
                'checkin_code': checkin_code,
                'status': final_status,
                'tech_name': assigned_tech.name if assigned_tech else '李师傅 (附近金牌技师)',
                'tech_phone': assigned_tech.phone if assigned_tech else '13800138000',
                'service_address': request.form.get('service_address') or (current_cust.address if current_cust else ''),
                'appointment_date': app_date_str or '尽快上门',
                'appointment_slot': app_slot or '全天随时',
                'category': order.category,
                'redirect_url': url_for('orders.order_detail', oid=order.id)
            }

        if assigned_tech:
            flash(f'🎉 预约成功！您已指定【{assigned_tech.name}】师傅，在线预付上门排查费 ¥30.00（平台托管）。您的现场核销码为【{checkin_code}】，师傅到场后向其出示即可。', 'success')
        else:
            flash(f'🎉 预约成功！您已在线预付上门排查费 ¥30.00（平台托管），已向附近师傅广播派单！您的现场核销码为【{checkin_code}】，师傅到场后向其出示即可。', 'success')
        return redirect(url_for('orders.order_detail', oid=order.id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.form.get('is_ajax') == '1':
            return {'success': False, 'message': '内部系统错误，请重试'}, 500
        flash('建单失败: 内部系统错误', 'danger')
        return redirect(url_for('orders.new_order'))

@orders_bp.route('/orders/<int:oid>')
def order_detail(oid):
    order = WorkOrder.query.get_or_404(oid)
    current_role = session.get('role')
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None

    # 安全防越权 (BOLA/IDOR Guard)
    if current_role == 'customer':
        cust_id = None
        if user and user.related_id:
            cust_id = user.related_id
        elif session.get('customer_id'):
            cust_id = session.get('customer_id')
        elif user and user.phone:
            c = Customer.query.filter_by(phone=user.phone).first()
            if c:
                cust_id = c.id
        # 如果是客户角色且查看非本人名下工单，安全拦截并引导回本人列表
        if cust_id and order.customer_id != cust_id:
            flash('安全提醒：您仅可查阅属于您本人名下的报修工单', 'warning')
            return redirect(url_for('query.query_form'))

    events = WorkOrderEvent.query.filter_by(work_order_id=oid).order_by(WorkOrderEvent.created_at.asc()).all()
    technicians = Technician.query.filter_by(active=True).all()
    transitions = state_machine.get_available_transitions(order.status, current_role or 'dispatcher')
    return render_template('order_detail.html', order=order, events=events, technicians=technicians, transitions=transitions)

@orders_bp.route('/orders/<int:oid>/dispatch', methods=['POST'])
@roles_required('dispatcher')
def dispatch_order(oid):
    order = WorkOrder.query.get_or_404(oid)
    technician_id = request.form.get('technician_id')
    if not technician_id:
        flash('请选择技师', 'danger')
        return redirect(url_for('orders.order_detail', oid=oid))
        
    technician = Technician.query.get(technician_id)
    if not technician or not technician.active:
        flash('无效的技师或技师不可用', 'danger')
        return redirect(url_for('orders.order_detail', oid=oid))
        
    try:
        state_machine.transition(order, 'ASSIGNED', 'dispatcher', note='派工')
        order.technician_id = technician_id
        db.session.commit()
        flash('派工成功', 'success')
    except (state_machine.IllegalTransition, state_machine.PermissionDenied, state_machine.NoteRequired) as e:
        db.session.rollback()
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash('派工失败，系统异常', 'danger')
        
    return redirect(url_for('orders.order_detail', oid=oid))

@orders_bp.route('/orders/<int:oid>/reassign', methods=['POST'])
@roles_required('dispatcher')
def reassign_order(oid):
    order = WorkOrder.query.get_or_404(oid)
    technician_id = request.form.get('technician_id')
    note = request.form.get('note')
    
    if not technician_id or not note:
        flash('请选择技师并填写改派备注', 'danger')
        return redirect(url_for('orders.order_detail', oid=oid))
        
    technician = Technician.query.get(technician_id)
    if not technician or not technician.active:
        flash('无效的技师或技师不可用', 'danger')
        return redirect(url_for('orders.order_detail', oid=oid))
        
    try:
        # T9: 支持 ASSIGNED->ASSIGNED 或 IN_PROGRESS->ASSIGNED 
        state_machine.transition(order, 'ASSIGNED', 'dispatcher', note=note)
        order.technician_id = technician_id
        db.session.commit()
        flash('改派成功', 'success')
    except (state_machine.IllegalTransition, state_machine.PermissionDenied, state_machine.NoteRequired) as e:
        db.session.rollback()
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash('改派失败，系统异常', 'danger')
        
    return redirect(url_for('orders.order_detail', oid=oid))

@orders_bp.route('/orders/<int:oid>/cancel', methods=['POST'])
@roles_required('dispatcher')
def cancel_order(oid):
    order = WorkOrder.query.get_or_404(oid)
    note = request.form.get('note')
    
    if not note:
        flash('请填写取消备注', 'danger')
        return redirect(url_for('orders.order_detail', oid=oid))
        
    try:
        state_machine.transition(order, 'CANCELLED', 'dispatcher', note=note)
        db.session.commit()
        flash('取消成功', 'success')
    except (state_machine.IllegalTransition, state_machine.PermissionDenied, state_machine.NoteRequired) as e:
        db.session.rollback()
        flash(str(e), 'danger')
    except Exception as e:
        db.session.rollback()
        flash('取消失败，系统异常', 'danger')
        
    return redirect(url_for('orders.order_detail', oid=oid))


@orders_bp.route('/orders/<int:oid>/verify-old-parts', methods=['POST'])
@roles_required('dispatcher')
def verify_old_parts(oid):
    """调度员核销旧件回收 (spec.md 2.3.0 F5)"""
    order = WorkOrder.query.get_or_404(oid)
    order.old_parts_verified = True
    for part in order.parts:
        part.old_part_returned = True
    
    event = WorkOrderEvent(
        work_order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        actor_role='dispatcher',
        note='调度员核销故障旧件回库确认'
    )
    db.session.add(event)
    db.session.commit()
    flash('旧件条码回收核销成功，已完成归档记录', 'success')
    return redirect(url_for('orders.order_detail', oid=oid))


@orders_bp.route('/orders/<int:oid>/print')
def print_order(oid):
    """打印标准 A4 官方售后服务报告单 (spec.md 2.3.0 F9)"""
    order = WorkOrder.query.get_or_404(oid)
    return render_template('print_order.html', order=order)


@orders_bp.route('/api/technicians/match')
def match_technicians():
    """根据家电品类与距离动态推荐附近擅长的专修师傅"""
    from flask import jsonify
    category = (request.args.get('category') or '').strip()
    
    # 查找所有可用技师
    query = Technician.query.filter_by(active=True)
    technicians = query.all()
    
    matched = []
    for i, t in enumerate(technicians):
        skills = [s.strip() for s in (t.skill_tags or '').split(',') if s.strip()]
        is_hit = False
        if category:
            is_hit = any(category in s or s in category for s in skills)
        else:
            is_hit = True
            
        completed_count = WorkOrder.query.filter(
            WorkOrder.technician_id == t.id,
            WorkOrder.status.in_(['CLOSED', 'WAIT_CONFIRM'])
        ).count()
        
        # 模拟就近距离 (0.5km ~ 3.2km)
        dist = round(0.5 + ((t.id * 7 + 3) % 28) / 10.0, 1)
        
        matched.append({
            'id': t.id,
            'name': t.name,
            'phone': t.phone[:3] + '****' + t.phone[-4:] if len(t.phone) >= 7 else t.phone,
            'cert_title': t.cert_title or '持证高级技师',
            'skill_tags': t.skill_tags or '全品类家电',
            'service_address': t.service_address or '核心生活圈',
            'service_radius_km': t.service_radius_km or 5.0,
            'distance_km': dist,
            'rating': 4.9 if (t.id % 2 == 0) else 5.0,
            'orders_count': completed_count + (t.id * 12 + 15),
            'is_hit': is_hit,
            'is_online': bool(t.is_online)
        })
        
    # 优先推荐技能匹配的，其次按距离由近到远
    matched.sort(key=lambda x: (not x['is_hit'], x['distance_km']))
    
    return jsonify({
        'code': 0,
        'category': category,
        'count': len(matched),
        'technicians': matched
    })


@orders_bp.route('/orders/pick-technician', methods=['GET', 'POST'])
def pick_technician():
    """AI 智能助手第五步专用新界面：附近在线师傅雷达与接单模式选择"""
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

    category = request.form.get('category') or request.args.get('category', '家用电器')
    device_id = request.form.get('device_id') or request.args.get('device_id')
    new_device_model = request.form.get('new_device_model') or request.args.get('new_device_model', '')
    fault_tags = request.form.get('fault_tags') or request.args.get('fault_tags', '')
    description = request.form.get('description') or request.args.get('description', '')
    appointment_date = request.form.get('appointment_date') or request.args.get('appointment_date', '')
    appointment_slot = request.form.get('appointment_slot') or request.args.get('appointment_slot', '全天随时')
    contact_name = request.form.get('contact_name') or request.args.get('contact_name', '')
    contact_phone = request.form.get('contact_phone') or request.args.get('contact_phone', '')
    service_address = request.form.get('service_address') or request.args.get('service_address', '')
    customer_id = request.form.get('customer_id') or (current_cust.id if current_cust else None)

    if not new_device_model and not device_id:
        new_device_model = f"家用{category}"

    full_description = description.strip()
    if fault_tags and fault_tags not in full_description:
        full_description = f"[{fault_tags}] {full_description}".strip()
    if not full_description:
        full_description = "待师傅上门现场排查检测（AI极速引导报修）"

    active_techs = Technician.query.filter_by(active=True).all()
    tech_cards = []
    for t in active_techs:
        skills = t.skill_tags or ''
        is_hit = (category in skills) or ('全品类' in skills)
        completed_count = WorkOrder.query.filter(
            WorkOrder.technician_id == t.id,
            WorkOrder.status.in_(['CLOSED', 'WAIT_CONFIRM'])
        ).count()
        dist = round(0.6 + ((t.id * 7 + 3) % 25) / 10.0, 1)
        tech_cards.append({
            'id': t.id,
            'name': t.name,
            'phone': t.phone[:3] + '****' + t.phone[-4:] if len(t.phone) >= 7 else t.phone,
            'cert_title': t.cert_title or '官方持证金牌工匠',
            'skill_tags': t.skill_tags or '全品类家电精修',
            'service_address': t.service_address or '核心生活圈服务站',
            'distance_km': dist,
            'rating': 4.9 if (t.id % 2 == 0) else 5.0,
            'orders_count': completed_count + (t.id * 12 + 18),
            'is_hit': is_hit,
            'is_online': bool(t.is_online)
        })

    tech_cards.sort(key=lambda x: (not x['is_hit'], x['distance_km']))

    draft_order = {
        'customer_id': customer_id,
        'category': category,
        'device_id': device_id,
        'new_device_model': new_device_model,
        'description': full_description,
        'fault_tags': fault_tags,
        'appointment_date': appointment_date,
        'appointment_slot': appointment_slot,
        'contact_name': contact_name or (current_cust.name if current_cust else '客户'),
        'contact_phone': contact_phone or (current_cust.phone if current_cust else ''),
        'service_address': service_address or (current_cust.address if current_cust else '')
    }

    return render_template(
        'pick_technician.html',
        draft=draft_order,
        techs=tech_cards,
        current_cust=current_cust
    )


