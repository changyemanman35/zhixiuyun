"""管理报表路由"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models import db, WorkOrder, FaultType, utcnow
from rules import calc_durations, is_on_time
import config
from datetime import datetime

bp = Blueprint('reports', __name__)

@bp.before_request
def check_permission():
    role = session.get('role')
    if role and role != 'dispatcher':
        role_zh = {'technician': '维修技师', 'customer': '报修客户'}.get(role, role)
        flash(f'权限受限：【{role_zh}】无权查看管理报表与统计下钻', 'error')
        if role == 'technician':
            return redirect(url_for('tech.tech_index'))
        else:
            return redirect(url_for('query.query_form'))

@bp.route('/reports', methods=['GET'])
def index():
    month_str = request.args.get('month')
    now = utcnow()
    default_month = f"{now.year}-{now.month:02d}"

    if month_str:
        try:
            target_date = datetime.strptime(month_str, '%Y-%m')
            target_year, target_month = target_date.year, target_date.month
        except ValueError:
            target_year, target_month = now.year, now.month
            month_str = default_month
    else:
        target_year, target_month = now.year, now.month
        month_str = default_month

    start_date = datetime(target_year, target_month, 1)
    if target_month == 12:
        end_date = datetime(target_year + 1, 1, 1)
    else:
        end_date = datetime(target_year, target_month + 1, 1)

    orders = WorkOrder.query.filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at < end_date
    ).all()

    total_count = len(orders)
    closed_orders = [o for o in orders if o.status == 'CLOSED']
    closed_count = len(closed_orders)

    on_time_count = 0
    evaluable_count = 0
    for o in closed_orders:
        ot = is_on_time(o)
        if ot is not None:
            evaluable_count += 1
            if ot:
                on_time_count += 1

    on_time_rate = (on_time_count / evaluable_count * 100) if evaluable_count > 0 else 0.0

    total_duration = 0.0
    duration_evaluable = 0
    for o in closed_orders:
        durs = calc_durations(o)
        if durs and durs.get('repair_duration') is not None:
            total_duration += durs['repair_duration']
            duration_evaluable += 1

    avg_repair_duration = (total_duration / duration_evaluable) if duration_evaluable > 0 else 0.0

    warranty_count = sum(1 for o in orders if o.warranty_flag)
    warranty_rate = (warranty_count / total_count * 100) if total_count > 0 else 0.0

    # 故障类型统计（排除未判定单，分子分母同源）
    fault_counts = {}
    unassigned_count = 0
    for o in orders:
        if o.fault_type and o.fault_type.name != '待技师判定':
            fid = o.fault_type.id
            fault_counts[fid] = fault_counts.get(fid, 0) + 1
        else:
            unassigned_count += 1

    total_valid_faults = sum(fault_counts.values())

    top_faults = []
    if total_valid_faults > 0:
        sorted_faults = sorted(fault_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for fid, count in sorted_faults:
            ft = FaultType.query.get(fid)
            if ft:
                top_faults.append({
                    'id': fid,
                    'name': ft.name,
                    'count': count,
                    'percentage': round(count / total_valid_faults * 100, 1)
                })

    # 超时单数量统计（用于下钻）
    late_count = sum(1 for o in closed_orders if is_on_time(o) is False)

    kpi = {
        'total_orders': total_count,
        'closed_orders': closed_count,
        'on_time_rate': on_time_rate,
        'avg_repair_hours': avg_repair_duration,
        'warranty_rate': warranty_rate,
        'top_faults': top_faults,
        'unassigned_count': unassigned_count,
        'late_count': late_count
    }

    return render_template('report.html', kpi=kpi, selected_month=month_str, config=config, has_data=total_count > 0)


@bp.route('/reports/list', methods=['GET'])
def report_list():
    month_str = request.args.get('month')
    kind = request.args.get('kind', 'all')
    fid = request.args.get('fid', type=int)

    now = utcnow()
    if not month_str:
        month_str = f"{now.year}-{now.month:02d}"

    try:
        target_date = datetime.strptime(month_str, '%Y-%m')
        target_year, target_month = target_date.year, target_date.month
    except ValueError:
        target_year, target_month = now.year, now.month
        month_str = f"{target_year}-{target_month:02d}"

    start_date = datetime(target_year, target_month, 1)
    if target_month == 12:
        end_date = datetime(target_year + 1, 1, 1)
    else:
        end_date = datetime(target_year, target_month + 1, 1)

    query = WorkOrder.query.filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at < end_date
    )

    if kind == 'closed':
        query = query.filter(WorkOrder.status == 'CLOSED')
    elif kind == 'warranty':
        query = query.filter(WorkOrder.warranty_flag == True)
    elif kind == 'fault' and fid:
        query = query.filter(WorkOrder.fault_type_id == fid)

    orders = query.all()

    result_orders = []
    for o in orders:
        durs = calc_durations(o)
        o.resp_duration = durs.get('response_duration')
        o.rep_duration = durs.get('repair_duration')

        ot = is_on_time(o)
        o.is_on_time_flag = ot
        if ot is True:
            o.on_time_text = '按时'
        elif ot is False:
            o.on_time_text = '超时'
        else:
            o.on_time_text = '不可判定'

        o.status_cn = config.STATUS_LABELS.get(o.status, o.status)

        if kind == 'late' and ot is not False:
            continue

        result_orders.append(o)

    kind_labels = {
        'all': '全部工单',
        'closed': '已关闭工单',
        'late': '超时关闭单',
        'warranty': '保内工单',
        'fault': '指定故障分类工单'
    }

    return render_template('report_list.html', orders=result_orders, month=month_str, kind=kind,
                           kind_label=kind_labels.get(kind, '工单列表'))


@bp.route('/reports/export', methods=['GET'])
def report_export_csv():
    """月度经营台账与财务报表一键导出 CSV（带 UTF-8 BOM，Excel 零乱码，spec.md 2.3.0 F10）"""
    import io, csv
    from flask import Response
    month_str = request.args.get('month')
    now = utcnow()
    if not month_str:
        month_str = f"{now.year}-{now.month:02d}"

    try:
        target_date = datetime.strptime(month_str, '%Y-%m')
        target_year, target_month = target_date.year, target_date.month
    except ValueError:
        target_year, target_month = now.year, now.month
        month_str = f"{target_year}-{target_month:02d}"

    start_date = datetime(target_year, target_month, 1)
    if target_month == 12:
        end_date = datetime(target_year + 1, 1, 1)
    else:
        end_date = datetime(target_year, target_month + 1, 1)

    orders = WorkOrder.query.filter(
        WorkOrder.created_at >= start_date,
        WorkOrder.created_at < end_date
    ).order_by(WorkOrder.created_at.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        '工单编号', '客户姓名', '客户电话', '服务设备', '设备SN',
        '工单状态', '优先级', '保修属性', '工时(小时)',
        '人工费(元)', '备件费(元)', '上门费(元)', '总费用(元)',
        '客户评分', '报修时间', '完工时间'
    ])

    for o in orders:
        cust_name = o.customer.name if o.customer else ''
        cust_phone = o.customer.phone if o.customer else ''
        dev_model = o.device.model if o.device else ''
        dev_sn = o.device.serial_no if (o.device and o.device.serial_no) else ''
        status_cn = config.STATUS_LABELS.get(o.status, o.status)
        warranty_str = '保内' if o.warranty_flag else '保外'
        created_str = o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else ''
        comp_str = o.completed_at.strftime('%Y-%m-%d %H:%M') if o.completed_at else ''
        rating_str = f"{o.rating}星" if o.rating else '未评价'

        writer.writerow([
            o.order_no, cust_name, cust_phone, dev_model, dev_sn,
            status_cn, o.priority, warranty_str, o.labor_hours or 0,
            f"{o.labor_fee:.2f}", f"{o.part_fee:.2f}", f"{o.visit_fee:.2f}", f"{o.total_fee:.2f}",
            rating_str, created_str, comp_str
        ])

    csv_data = '\ufeff' + output.getvalue()
    filename = f"ASM_Monthly_Report_{month_str}.csv"
    return Response(
        csv_data,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

