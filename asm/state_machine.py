"""ASM 状态机引擎 ── 10 条合法转移，其余一律拒绝
铁律1：状态变更只能走 transition()，路由层禁止直接给 status 赋值
铁律3：状态变更与事件日志同一事务提交
"""
from models import db, WorkOrderEvent, utcnow


# ── 自定义异常 ──

class IllegalTransition(Exception):
    """非法状态转移"""
    def __init__(self, from_status, to_status):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f'非法状态转移: {from_status} → {to_status}')


class PermissionDenied(Exception):
    """角色权限不足"""
    def __init__(self, actor_role, expected):
        self.actor_role = actor_role
        self.expected = expected
        super().__init__(f'权限不足: 需要 {expected}，当前 {actor_role}')


class NoteRequired(Exception):
    """缺少必填原因"""
    def __init__(self, event_name):
        self.event_name = event_name
        super().__init__(f'{event_name}必须填写原因')


# ── 10 条合法转移（声明式，非 if-else 链）──
# key = (from_status, to_status)
# value = {"actor": ..., "event": ..., "require_note": bool}
TRANSITIONS = {
    ('PENDING',      'ASSIGNED'):     {'actor': 'dispatcher',  'event': '派工'},
    ('ASSIGNED',     'IN_PROGRESS'):  {'actor': 'technician',  'event': '开工'},
    ('IN_PROGRESS',  'WAIT_CONFIRM'): {'actor': 'technician',  'event': '完工'},
    ('IN_PROGRESS',  'ON_HOLD'):      {'actor': 'technician',  'event': '挂起',  'require_note': True},
    ('ON_HOLD',      'IN_PROGRESS'):  {'actor': 'technician',  'event': '恢复'},
    ('WAIT_CONFIRM', 'CLOSED'):       {'actor': 'customer',    'event': '确认'},
    ('WAIT_CONFIRM', 'IN_PROGRESS'):  {'actor': 'customer',    'event': '返工',  'require_note': True},
    ('ASSIGNED',     'ASSIGNED'):     {'actor': 'dispatcher',  'event': '改派',  'require_note': True},
    ('PENDING',      'CANCELLED'):    {'actor': 'dispatcher',  'event': '取消',  'require_note': True},
    ('ASSIGNED',     'CANCELLED'):    {'actor': 'dispatcher',  'event': '取消',  'require_note': True},
}


def can_transition(from_status, to_status):
    """检查转移是否合法（不检查角色和原因）"""
    return (from_status, to_status) in TRANSITIONS


def get_available_transitions(status, actor_role=None):
    """获取某状态下所有可用转移"""
    result = []
    for (f, t), spec in TRANSITIONS.items():
        if f == status:
            if actor_role is None or spec['actor'] == actor_role:
                result.append((t, spec))
    return result


def transition(order, to_status, actor_role, actor_id=None, note=None, now=None):
    """执行状态转移（唯一入口）

    Args:
        order: WorkOrder 实例
        to_status: 目标状态
        actor_role: 操作者角色
        actor_id: 操作者 ID（可选）
        note: 原因/备注
        now: 当前时刻（测试用注入，默认 utcnow()）

    Raises:
        IllegalTransition: 非法转移
        PermissionDenied: 角色权限不足
        NoteRequired: 缺必填原因

    Returns:
        WorkOrderEvent: 本次转移生成的事件
    """
    if now is None:
        now = utcnow()

    key = (order.status, to_status)
    spec = TRANSITIONS.get(key)

    # SM-1：非法转移一律拒绝
    if spec is None:
        raise IllegalTransition(order.status, to_status)

    # SM-4：角色权限校验
    if spec['actor'] != actor_role:
        raise PermissionDenied(actor_role, spec['actor'])

    # UI-4：必填原因校验
    if spec.get('require_note') and not (note and note.strip()):
        raise NoteRequired(spec['event'])

    # 同一事务：状态变更 + 事件日志（铁律3）
    event = WorkOrderEvent(
        work_order_id=order.id,
        from_status=order.status,
        to_status=to_status,
        actor_role=actor_role,
        actor_id=actor_id,
        note=note.strip() if note else None,
        created_at=now,
    )

    old_status = order.status
    order.status = to_status

    # ── 副作用（写时间戳等）──
    if old_status == 'PENDING' and to_status == 'ASSIGNED':
        # T2 派工：写 dispatched_at
        order.dispatched_at = now

    elif old_status == 'ASSIGNED' and to_status == 'ASSIGNED':
        # T9 改派：dispatched_at 保持不变（铁律4）
        pass

    elif to_status == 'WAIT_CONFIRM' and old_status == 'IN_PROGRESS':
        # T4 完工：写 completed_at（费用由路由层在调用前计算好）
        order.completed_at = now

    elif to_status == 'CLOSED':
        # T7 确认关单：写 closed_at
        order.closed_at = now

    elif old_status == 'WAIT_CONFIRM' and to_status == 'IN_PROGRESS':
        # T8 返工：清空 completed_at、工时与四项费用
        order.completed_at = None
        order.labor_hours = None
        order.labor_fee = 0.0
        order.part_fee = 0.0
        order.visit_fee = 0.0
        order.total_fee = 0.0
        order.fault_type_id = None
        order.resolution = None
        order.resolution_note = None

    db.session.add(event)
    # 注意：不在此处 commit，由调用方统一 commit（路由层负责事务边界）
    return event
