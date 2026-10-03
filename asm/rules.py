"""ASM 业务规则 ── 保修判定 / 费用计算 / SLA 判定 / 时长计算
四条规则有唯一实现，报表与页面必须复用同一份
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import config


def _add_months(d, months):
    """给日期加 N 个月（精确月份计算）"""
    try:
        return d + relativedelta(months=months)
    except Exception:
        # 若 dateutil 不可用，退化为近似计算
        return d + timedelta(days=months * 30)


# ── 保修判定（02 §4.2）──

def warranty_breakdown(device, ref_date=None):
    """计算保修截止日和保修状态

    Args:
        device: Device 实例（需 purchase_date, warranty_months, warranty_override_date）
        ref_date: 判定基准日期（默认今天）

    Returns:
        dict: {
            'base_end': 原截止日,
            'override_end': 延保截止日或 None,
            'actual_end': 实际截止日（取 max）,
            'is_warranty': bool
        }
    """
    if ref_date is None:
        ref_date = date.today()

    base_end = _add_months(device.purchase_date, device.warranty_months)
    override_end = device.warranty_override_date

    if override_end is not None:
        actual_end = max(base_end, override_end)  # WR-3：只取有利方向
    else:
        actual_end = base_end

    # B-3：到期当天仍算保内（<=）
    is_warranty = (ref_date <= actual_end)

    return {
        'base_end': base_end,
        'override_end': override_end,
        'actual_end': actual_end,
        'is_warranty': is_warranty,
    }


def judge_warranty(device, created_at):
    """判定工单保修状态（建单时调用）

    Args:
        device: Device 实例
        created_at: datetime，工单创建时刻

    Returns:
        tuple: (warranty_flag: bool, actual_end: date)
    """
    ref_date = created_at.date() if hasattr(created_at, 'date') else created_at
    info = warranty_breakdown(device, ref_date)
    return info['is_warranty'], info['actual_end']


# ── 费用计算（02 §4.3）──

def calc_fee(order, parts_detail=None, labor_hours=None):
    """计算费用四项

    Args:
        order: WorkOrder（需 warranty_flag, priority）
        parts_detail: [(unit_price, quantity), ...] 配件明细
        labor_hours: 工时（小时）

    Returns:
        dict: {labor_fee, part_fee, visit_fee, total_fee}
    """
    if order.warranty_flag:
        # 保内：一律 0
        return {'labor_fee': 0.0, 'part_fee': 0.0, 'visit_fee': 0.0, 'total_fee': 0.0}

    # 保外
    labor_h = labor_hours or 0.0
    labor_fee = round(labor_h * config.LABOR_RATE_PER_HOUR, 2)

    part_fee = 0.0
    if parts_detail:
        for price, qty in parts_detail:
            part_fee += round(price * qty, 2)
    part_fee = round(part_fee, 2)

    if order.priority == 'urgent':
        visit_fee = config.VISIT_FEE_URGENT
    else:
        visit_fee = config.VISIT_FEE_NORMAL

    total_fee = round(labor_fee + part_fee + visit_fee, 2)

    return {
        'labor_fee': labor_fee,
        'part_fee': part_fee,
        'visit_fee': visit_fee,
        'total_fee': total_fee,
    }


# ── SLA 预警判定（02 §4.4）──

def sla_level(order, now=None):
    """判定工单当前 SLA 级别

    Args:
        order: WorkOrder
        now: 当前时刻

    Returns:
        str: 'normal' / 'warn' / 'danger'
    """
    from models import utcnow
    if now is None:
        now = utcnow()

    status = order.status

    if status == 'PENDING' and order.created_at:
        hours = (now - order.created_at).total_seconds() / 3600
        if hours > config.SLA_DISPATCH_HOURS:
            return 'warn'

    elif status == 'IN_PROGRESS' and order.dispatched_at:
        hours = (now - order.dispatched_at).total_seconds() / 3600
        if hours > config.SLA_PROGRESS_DANGER_HOURS:
            return 'danger'
        if hours > config.SLA_PROGRESS_HOURS:
            return 'warn'

    elif status == 'ASSIGNED' and order.dispatched_at:
        # 已派工但未开工，也看停留时间
        hours = (now - order.dispatched_at).total_seconds() / 3600
        if hours > config.SLA_PROGRESS_HOURS:
            return 'warn'

    elif status == 'WAIT_CONFIRM' and order.completed_at:
        hours = (now - order.completed_at).total_seconds() / 3600
        if hours > config.SLA_CONFIRM_HOURS:
            return 'warn'

    elif status == 'ON_HOLD':
        # AC-4.3：挂起不判 danger
        return 'warn'  # 挂起本身就是需要关注的

    return 'normal'


# ── 时长计算（02 §4.5）──

def calc_durations(order):
    """计算三个时长（小时）

    Returns:
        dict: {response_duration, repair_duration, closure_duration}
              未完成的段返回 None
    """
    response = None
    repair = None
    closure = None

    if order.dispatched_at and order.created_at:
        response = round((order.dispatched_at - order.created_at).total_seconds() / 3600, 1)

    if order.completed_at and order.dispatched_at:
        repair = round((order.completed_at - order.dispatched_at).total_seconds() / 3600, 1)

    if order.closed_at and order.completed_at:
        closure = round((order.closed_at - order.completed_at).total_seconds() / 3600, 1)

    return {
        'response_duration': response,
        'repair_duration': repair,
        'closure_duration': closure,
    }


# ── 按时关闭判定（02 §4.5.1）──

def is_on_time(order):
    """判定已关闭工单是否按时

    Returns:
        True=按时, False=超时, None=不可判定
    """
    if order.status != 'CLOSED':
        return None

    durations = calc_durations(order)
    resp = durations['response_duration']
    repair = durations['repair_duration']

    # 锚点缺失→不可判定
    if resp is None or repair is None:
        return None

    # 两段都达标 = 按时
    if resp <= config.SLA_DISPATCH_HOURS and repair <= config.SLA_PROGRESS_HOURS:
        return True
    return False


# ── 工单号生成（02 §4.1）──

def generate_order_no(created_at, db_session):
    """生成工单号 WO-YYYYMMDD-####

    规则：取当日最大序号+1（SEED-3：不用条数+1，避免清空后撞号）
    """
    from models import WorkOrder
    date_str = created_at.strftime('%Y%m%d')
    prefix = f'WO-{date_str}-'

    # 查当日最大序号
    last = (db_session.query(WorkOrder.order_no)
            .filter(WorkOrder.order_no.like(f'{prefix}%'))
            .order_by(WorkOrder.order_no.desc())
            .first())

    if last and last[0]:
        try:
            seq = int(last[0].split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    return f'{prefix}{seq:04d}'


# ── 工时预填（FR-FEE-2）──

def prefill_labor_hours(order, now=None):
    """计算技师完工表单的工时预填值

    = (当前时刻 - dispatched_at) / 3600，保留一位小数
    落在 0.5-24h 区间
    """
    from models import utcnow
    if now is None:
        now = utcnow()

    if not order.dispatched_at:
        return config.LABOR_HOURS_MIN

    hours = (now - order.dispatched_at).total_seconds() / 3600
    hours = round(hours, 1)
    hours = max(config.LABOR_HOURS_MIN, min(config.LABOR_HOURS_MAX, hours))
    return hours


# ── 智能派工推荐与 30 天二次返修雷达（spec.md 2.3.0）──

def is_rework_30d(order, db_session):
    """判定该设备在当前工单创建时刻前 30 天内是否报修过（返修雷达预警）"""
    from models import WorkOrder
    if not order or not order.device_id or not order.created_at:
        return False

    threshold = order.created_at - timedelta(days=30)
    query = db_session.query(WorkOrder).filter(
        WorkOrder.device_id == order.device_id,
        WorkOrder.created_at >= threshold,
        WorkOrder.created_at < order.created_at,
        WorkOrder.status != 'CANCELLED'
    )
    if order.id:
        query = query.filter(WorkOrder.id != order.id)
    return query.count() > 0


def recommend_technician(order, technicians, db_session):
    """智能派工推荐算法：
    Score = (SkillMatch * 50) - (ActiveOrders * 15)
    返回按分数降序排列的列表：[(tech, score, match_reason), ...]
    """
    from models import WorkOrder
    results = []

    # 提取工单故障或描述关键词
    target_keywords = []
    if order.fault_type and order.fault_type.name:
        target_keywords.append(order.fault_type.name.lower())
    if order.description:
        target_keywords.append(order.description.lower())
    if order.device and order.device.model:
        target_keywords.append(order.device.model.lower())

    for tech in technicians:
        if not tech.active:
            continue

        # 1. 技能匹配判定
        skill_match = 0
        match_desc = '通用标准工程师'
        if tech.skill_tags:
            tags = [t.strip().lower() for t in tech.skill_tags.split(',') if t.strip()]
            for kw in target_keywords:
                for tag in tags:
                    if tag in kw or kw in tag:
                        skill_match = 1
                        match_desc = f'精修{tag}'
                        break
                if skill_match:
                    break

        # 2. 在途活动单负荷统计 (ASSIGNED / IN_PROGRESS / ON_HOLD)
        active_orders = db_session.query(WorkOrder).filter(
            WorkOrder.technician_id == tech.id,
            WorkOrder.status.in_(['ASSIGNED', 'IN_PROGRESS', 'ON_HOLD'])
        ).count()

        # 3. 综合评分计算
        score = (skill_match * 50) - (active_orders * 15)
        reason = f"{match_desc} (当前在手: {active_orders}单)"
        results.append({
            'technician': tech,
            'score': score,
            'skill_match': bool(skill_match),
            'active_orders': active_orders,
            'reason': reason
        })

    # 按综合评分降序排列
    results.sort(key=lambda x: x['score'], reverse=True)
    return results
