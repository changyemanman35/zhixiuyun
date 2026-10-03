from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from models import db, WorkOrder, WorkOrderEvent, Customer, OrderPart, User, utcnow
import state_machine
import rules
import config

query_bp = Blueprint('query', __name__)


def mask_phone(phone):
    """手机号脱敏：保留前3后4"""
    if not phone or len(phone) < 7:
        return phone
    return f"{phone[:3]}{'*' * (len(phone) - 7)}{phone[-4:]}"


@query_bp.route('/query', methods=['GET', 'POST'])
def query_form():
    """客户查询页（支持客户登录专属工单列表与免登录双凭证查询）"""
    my_orders = []
    current_cust = None
    user_id = session.get('user_id')
    role = session.get('role')

    # 如果是已登录客户，加载名下客户实体与全部历史工单
    if user_id and role == 'customer':
        user = User.query.get(user_id)
        if user and user.related_id:
            current_cust = Customer.query.get(user.related_id)
        elif user and user.phone:
            current_cust = Customer.query.filter_by(phone=user.phone).first()

        if current_cust:
            my_orders = WorkOrder.query.filter_by(customer_id=current_cust.id).order_by(WorkOrder.created_at.desc()).all()

    if request.method == 'GET':
        order_no = request.args.get('order_no', '')
        # 如果客户已登录且传入了属于自己的 order_no，直接免输手机号呈现详情
        if order_no and current_cust:
            matched = WorkOrder.query.filter_by(order_no=order_no, customer_id=current_cust.id).first()
            if matched:
                events = (WorkOrderEvent.query
                          .filter_by(work_order_id=matched.id)
                          .order_by(WorkOrderEvent.created_at.asc()).all())
                durations = rules.calc_durations(matched)
                show_fee = matched.status in ('WAIT_CONFIRM', 'CLOSED') and matched.completed_at is not None
                return render_template('query.html',
                                       order=matched,
                                       events=events,
                                       masked_phone=mask_phone(current_cust.phone),
                                       raw_phone=current_cust.phone,
                                       durations=durations,
                                       show_fee=show_fee,
                                       config=config,
                                       my_orders=my_orders,
                                       current_cust=current_cust)
        return render_template('query.html', order_no=order_no, my_orders=my_orders, current_cust=current_cust)

    order_no = request.form.get('order_no', '').strip()
    phone = request.form.get('phone', '').strip()

    # 查找工单
    order = WorkOrder.query.filter_by(order_no=order_no).first()

    # AC-5.2：两种失败情形（工单不存在 vs 手机号不匹配）响应完全一致
    FAIL_MSG = '未找到匹配的工单信息，请核实工单号和手机号后重试'
    if not order or not order.customer or order.customer.phone != phone:
        return render_template('query.html', error=FAIL_MSG)

    # 命中：准备展示数据
    events = (WorkOrderEvent.query
              .filter_by(work_order_id=order.id)
              .order_by(WorkOrderEvent.created_at.asc()).all())

    durations = rules.calc_durations(order)
    masked = mask_phone(phone)

    # 费用展示逻辑
    show_fee = order.status in ('WAIT_CONFIRM', 'CLOSED') and order.completed_at is not None

    return render_template('query.html',
                           order=order,
                           events=events,
                           masked_phone=masked,
                           raw_phone=phone,
                           durations=durations,
                           show_fee=show_fee,
                           config=config)


@query_bp.route('/query/confirm', methods=['POST'])
def confirm_order():
    """客户确认完工"""
    order_no = request.form.get('order_no', '').strip()
    phone = request.form.get('phone', '').strip()

    order = WorkOrder.query.filter_by(order_no=order_no).first()
    if not order or not order.customer or order.customer.phone != phone:
        flash('验证失败，无法确认工单', 'error')
        return redirect(url_for('query.query_form'))

    # 已关闭：重复确认
    if order.status == 'CLOSED':
        flash('该工单已关闭。如需继续服务，请联系客服新建工单并关联原单号', 'warning')
        return redirect(url_for('query.query_form', order_no=order_no))

    try:
        state_machine.transition(order, 'CLOSED', 'customer', note='客户确认完工')
        db.session.commit()
        flash('确认成功！感谢您的反馈', 'success')
    except (state_machine.IllegalTransition, state_machine.PermissionDenied) as e:
        db.session.rollback()
        flash(f'无法确认：{e}', 'error')
    except Exception:
        db.session.rollback()
        flash('系统异常，请稍后重试', 'error')

    return redirect(url_for('query.query_form', order_no=order_no))


@query_bp.route('/query/rework', methods=['POST'])
def rework_order():
    """客户申请返工"""
    order_no = request.form.get('order_no', '').strip()
    phone = request.form.get('phone', '').strip()
    note = request.form.get('note', '').strip()

    if not note:
        flash('请填写返工原因', 'error')
        return redirect(url_for('query.query_form', order_no=order_no))

    order = WorkOrder.query.filter_by(order_no=order_no).first()
    if not order or not order.customer or order.customer.phone != phone:
        flash('验证失败，无法申请返工', 'error')
        return redirect(url_for('query.query_form'))

    try:
        state_machine.transition(order, 'IN_PROGRESS', 'customer', note=note)
        # 清空配件明细
        OrderPart.query.filter_by(order_id=order.id).delete()
        db.session.commit()
        flash('返工申请成功，工单已重新流转', 'success')
    except (state_machine.IllegalTransition, state_machine.PermissionDenied,
            state_machine.NoteRequired) as e:
        db.session.rollback()
        flash(f'返工失败：{e}', 'error')
    except Exception:
        db.session.rollback()
        flash('系统异常，请稍后重试', 'error')

    return redirect(url_for('query.query_form', order_no=order_no))


@query_bp.route('/query/rate', methods=['POST'])
def rate_order():
    """客户提交完工满意度星级打分与评价 (spec.md 2.3.0 F3)"""
    order_no = request.form.get('order_no', '').strip()
    phone = request.form.get('phone', '').strip()
    rating = request.form.get('rating')
    rating_tags = request.form.get('rating_tags', '').strip()
    rating_comment = request.form.get('rating_comment', '').strip()

    order = WorkOrder.query.filter_by(order_no=order_no).first()
    if not order or not order.customer or order.customer.phone != phone:
        flash('验证失败，无法提交评价', 'error')
        return redirect(url_for('query.query_form'))

    try:
        r_val = int(rating) if rating else 5
        order.rating = max(1, min(5, r_val))
        order.rating_tags = rating_tags
        order.rating_comment = rating_comment
        order.rated_at = utcnow()
        db.session.commit()
        flash('感谢您的星级评价与宝贵建议！官方售后因您而更专业。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'评价提交失败: {e}', 'error')

    return redirect(url_for('query.query_form', order_no=order_no))
