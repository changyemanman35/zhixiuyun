"""演示数据管理路由"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models import db, WorkOrder, WorkOrderEvent, OrderPart, Customer
import rules
import seed as seed_module
import config

bp = Blueprint('demo', __name__)

@bp.before_request
def check_permission():
    role = session.get('role')
    if role and role != 'dispatcher':
        role_zh = {'technician': '维修技师', 'customer': '报修客户'}.get(role, role)
        flash(f'权限受限：【{role_zh}】无权访问演示数据管理板块', 'error')
        if role == 'technician':
            return redirect(url_for('tech.tech_index'))
        else:
            return redirect(url_for('query.query_form'))

@bp.route('/seed', methods=['GET'])
def seed_page():
    """演示数据页"""
    demo_orders_list = WorkOrder.query.filter_by(is_demo=True).all()
    total = len(demo_orders_list)

    # 状态分布
    status_dist = {}
    for s in config.STATUSES:
        count = sum(1 for o in demo_orders_list if o.status == s)
        if count > 0:
            status_dist[s] = count

    # 超时关闭数
    late_closed = sum(1 for o in demo_orders_list
                      if o.status == 'CLOSED' and rules.is_on_time(o) is False)

    # 客户查询凭证（找一张 WAIT_CONFIRM 的单）
    demo_credential_orders = [o for o in demo_orders_list
                              if o.status in ('WAIT_CONFIRM', 'CLOSED')]

    return render_template('seed.html',
                           total=total,
                           status_dist=status_dist,
                           late_closed=late_closed,
                           statuses_covered=len(status_dist),
                           demo_orders=demo_credential_orders[:5],
                           config=config,
                           has_data=total > 0)


@bp.route('/seed/generate', methods=['POST'])
def seed_generate():
    """生成/追加演示数据"""
    mode = request.form.get('mode', 'append')
    try:
        if mode == 'reset':
            seed_module.clear_demo_data()
        count = seed_module.generate_demo_data(mode=mode)
        flash(f'演示数据生成成功（{count} 张工单）', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'生成失败: {str(e)}', 'error')
    return redirect(url_for('demo.seed_page'))


@bp.route('/seed/clear', methods=['POST'])
def seed_clear():
    """清空演示数据（SEED-2：只删 is_demo 工单，主数据保留）"""
    try:
        n = seed_module.clear_demo_data()
        flash(f'已清空 {n} 张演示工单，主数据已保留', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'清空失败: {str(e)}', 'error')
    return redirect(url_for('demo.seed_page'))
