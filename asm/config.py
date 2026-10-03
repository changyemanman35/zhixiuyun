"""ASM 全局配置 ── 所有业务参数集中于此，代码和模板中禁止硬编码"""
import os

# ── 数据库 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'asm.db')
SECRET_KEY = os.environ.get('ASM_SECRET_KEY', 'asm-dev-secret-key-2026')

# ── 费用 ──
LABOR_RATE_PER_HOUR = 80.0        # 保外工时单价（元/小时）
VISIT_FEE_NORMAL = 50.0           # 普通单上门费
VISIT_FEE_URGENT = 80.0           # 加急单上门费

# ── 保修 ──
DEFAULT_WARRANTY_MONTHS = 12

# ── SLA 阈值（自然小时，v1 简化，不排除夜间与周末）──
SLA_DISPATCH_HOURS = 4            # PENDING 未派工超时黄线
SLA_PROGRESS_HOURS = 48           # IN_PROGRESS 超时黄线
SLA_PROGRESS_DANGER_HOURS = 72    # IN_PROGRESS 严重超时红线
SLA_CONFIRM_HOURS = 72            # WAIT_CONFIRM 未确认超时黄线

# ── 工时输入约束 ──
LABOR_HOURS_MIN = 0.5
LABOR_HOURS_MAX = 24.0
LABOR_HOURS_STEP = 0.5

# ── 处理方式（字典化，禁止模板硬编码）──
RESOLUTIONS = ['更换配件', '调试修复', '远程指导', '无法修复']

# ── 文本长度 ──
DESCRIPTION_MAX = 500
NOTE_MAX = 200

# ── 状态定义 ──
STATUSES = [
    'PENDING', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD',
    'WAIT_CONFIRM', 'CLOSED', 'CANCELLED',
]

# ── 状态中文名（调度员 / 技师视角）──
STATUS_LABELS = {
    'PENDING':      '待受理',
    'ASSIGNED':     '已派工',
    'IN_PROGRESS':  '处理中',
    'ON_HOLD':      '已挂起',
    'WAIT_CONFIRM': '待确认',
    'CLOSED':       '已关闭',
    'CANCELLED':    '已取消',
}

# ── 状态中文名（客户视角）──
STATUS_LABELS_CUSTOMER = {
    'PENDING':      '已受理',
    'ASSIGNED':     '已安排技师',
    'IN_PROGRESS':  '维修中',
    'ON_HOLD':      '等配件',
    'WAIT_CONFIRM': '待您确认',
    'CLOSED':       '已完成',
    'CANCELLED':    '已取消',
}

# ── 状态色板（UI-1）──
STATUS_COLORS = {
    'PENDING':      '#9e9e9e',
    'ASSIGNED':     '#2196f3',
    'IN_PROGRESS':  '#00bcd4',
    'ON_HOLD':      '#ff9800',
    'WAIT_CONFIRM': '#9c27b0',
    'CLOSED':       '#4caf50',
    'CANCELLED':    '#bdbdbd',
}

# ── 演示数据 ──
BATCH_RNG_SEED = 20261001
