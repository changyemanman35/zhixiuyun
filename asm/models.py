"""ASM 数据模型 ── 11 张表，严格对照 spec.md 2.3.0 规格"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """UTC naive datetime（铁律5：时间一律存 UTC naive）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True, index=True)
    company = db.Column(db.String(128), nullable=True)
    address = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    devices = db.relationship('Device', backref='customer', lazy='dynamic')


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    model = db.Column(db.String(128), nullable=False)
    serial_no = db.Column(db.String(64), unique=True, nullable=True)
    purchase_date = db.Column(db.Date, nullable=False)
    warranty_months = db.Column(db.Integer, nullable=False, default=12)
    warranty_override_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class Technician(db.Model):
    __tablename__ = 'technicians'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    skill_tags = db.Column(db.String(256), nullable=True)  # 如 "空调,洗衣机,冰箱"
    cert_title = db.Column(db.String(100), nullable=True, default='持证家电维修高级工')
    service_address = db.Column(db.String(200), nullable=True, default='城市中心商圈')
    service_radius_km = db.Column(db.Float, nullable=False, default=5.0)
    balance = db.Column(db.Float, nullable=False, default=0.0)  # 师傅钱包收益余额
    is_online = db.Column(db.Boolean, nullable=False, default=True)  # 是否开启接单模式
    active = db.Column(db.Boolean, nullable=False, default=True)
    
    # 技师能力画像与接单档案扩展
    years_of_exp = db.Column(db.Integer, nullable=True, default=5)
    tools_checked = db.Column(db.String(256), nullable=True, default='数字万用表,双表阀充氟表,高空防坠安全绳')
    preferred_brands = db.Column(db.String(256), nullable=True, default='格力,美的,海尔,西门子')
    night_order_enabled = db.Column(db.Boolean, nullable=False, default=True)
    profile_completed = db.Column(db.Boolean, nullable=False, default=False)
    
    created_at = db.Column(db.DateTime, default=utcnow)


class FaultType(db.Model):
    __tablename__ = 'fault_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)


class Part(db.Model):
    __tablename__ = 'parts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    unit_price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=100)
    min_stock_alert = db.Column(db.Integer, nullable=False, default=10)


class OrderPart(db.Model):
    """工单配件明细（关联表）── 存快照价，改价不回溯（FR-FEE-1），含旧件防漏追溯"""
    __tablename__ = 'order_parts'

    order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'), primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)  # 提交时刻的快照价
    old_part_sn = db.Column(db.String(60), nullable=True)
    old_part_returned = db.Column(db.Boolean, nullable=False, default=False)

    part = db.relationship('Part')


class WorkOrder(db.Model):
    __tablename__ = 'work_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(24), nullable=False, unique=True, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('technicians.id'), nullable=True)
    fault_type_id = db.Column(db.Integer, db.ForeignKey('fault_types.id'), nullable=True)
    description = db.Column(db.String(500), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default='normal')
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    dispatched_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    warranty_flag = db.Column(db.Boolean, nullable=False, default=False)
    labor_fee = db.Column(db.Float, nullable=False, default=0.0)
    part_fee = db.Column(db.Float, nullable=False, default=0.0)
    visit_fee = db.Column(db.Float, nullable=False, default=0.0)
    total_fee = db.Column(db.Float, nullable=False, default=0.0)
    labor_hours = db.Column(db.Float, nullable=True)
    resolution = db.Column(db.String(20), nullable=True)
    resolution_note = db.Column(db.String(200), nullable=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)

    # 2.1 & 2.2 扩展字段
    appointment_date = db.Column(db.Date, nullable=True)
    appointment_slot = db.Column(db.String(30), nullable=True)
    rating = db.Column(db.Integer, nullable=True)
    rating_tags = db.Column(db.String(200), nullable=True)
    rating_comment = db.Column(db.Text, nullable=True)
    rated_at = db.Column(db.DateTime, nullable=True)
    old_parts_verified = db.Column(db.Boolean, nullable=False, default=False)

    # 3.0 C2C 撮合与线上上门费托管字段
    category = db.Column(db.String(50), nullable=True)  # AI 提取家电品类（如 空调、冰箱、洗衣机）
    pay_status = db.Column(db.String(20), nullable=False, default='PAID')  # UNPAID / PAID (托管中) / SETTLED (已核销分账) / REFUNDED (已退款)
    checkin_code = db.Column(db.String(6), nullable=True)  # 6 位现场打卡核销动态验证码
    checkin_at = db.Column(db.DateTime, nullable=True)     # 师傅现场核销打卡时间
    platform_commission = db.Column(db.Float, nullable=False, default=5.0)  # 平台技术撮合服务费
    offline_status = db.Column(db.String(30), nullable=True) # FIXED_OFFLINE (现场已修好) / ABORTED_OFFLINE (现场放弃维修)

    customer = db.relationship('Customer', backref='work_orders')
    device = db.relationship('Device', backref='work_orders')
    technician = db.relationship('Technician', backref='work_orders')
    fault_type = db.relationship('FaultType', backref='work_orders')
    events = db.relationship('WorkOrderEvent', backref='work_order',
                             order_by='WorkOrderEvent.created_at', lazy='dynamic',
                             cascade='all, delete-orphan')
    parts = db.relationship('OrderPart', backref='work_order', lazy='dynamic',
                            cascade='all, delete-orphan')


class WorkOrderEvent(db.Model):
    """状态流转日志 ── 只追加、不修改、不删除（SM-2 / NFR-5）"""
    __tablename__ = 'work_order_events'

    id = db.Column(db.Integer, primary_key=True)
    work_order_id = db.Column(db.Integer, db.ForeignKey('work_orders.id'),
                              nullable=False, index=True)
    from_status = db.Column(db.String(20), nullable=True)   # NULL = 创建事件
    to_status = db.Column(db.String(20), nullable=False)
    actor_role = db.Column(db.String(20), nullable=False)
    actor_id = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class User(db.Model):
    """用户账户表 ── 支持调度员、技师、客户等角色的注册与登录认证"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # dispatcher / technician / customer
    name = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)  # 关联的具体 customer.id 或 technician.id
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class ServiceStation(db.Model):
    """官方授权服务网点表"""
    __tablename__ = 'service_stations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    business_hours = db.Column(db.String(100), nullable=False, default='周一至周日 08:30-18:00')
    coverage_area = db.Column(db.String(200), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Notification(db.Model):
    """全角色模拟短信与站内通知表"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # customer / technician / dispatcher / all
    phone = db.Column(db.String(20), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), nullable=False, default='system')  # sms_mock / system / alert
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class AIChatLog(db.Model):
    """三端通用 AI 智能助手 (ASM Copilot) 对话审计日志"""
    __tablename__ = 'ai_chat_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='guest')
    user_prompt = db.Column(db.Text, nullable=False)
    sanitized_prompt = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    intent_detected = db.Column(db.String(50), nullable=False, default='general')
    engine_used = db.Column(db.String(30), nullable=False, default='local_expert')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


def init_db(app):
    """初始化数据库并安全补齐缺失列（支持平滑热升级）"""
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import inspect, text
            engine = db.engine
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if 'work_orders' in tables:
                wo_cols = [c['name'] for c in inspector.get_columns('work_orders')]
                cols_to_add = [
                    ('started_at', 'DATETIME'),
                    ('appointment_date', 'DATE'),
                    ('appointment_slot', 'VARCHAR(30)'),
                    ('rating', 'INTEGER'),
                    ('rating_tags', 'VARCHAR(200)'),
                    ('rating_comment', 'TEXT'),
                    ('rated_at', 'DATETIME'),
                    ('old_parts_verified', 'BOOLEAN DEFAULT 0'),
                    ('category', 'VARCHAR(50)'),
                    ('pay_status', "VARCHAR(20) DEFAULT 'PAID'"),
                    ('checkin_code', 'VARCHAR(6)'),
                    ('checkin_at', 'DATETIME'),
                    ('platform_commission', 'FLOAT DEFAULT 5.0'),
                    ('offline_status', 'VARCHAR(30)'),
                ]
                with engine.connect() as conn:
                    for c_name, c_type in cols_to_add:
                        if c_name not in wo_cols:
                            conn.execute(text(f"ALTER TABLE work_orders ADD COLUMN {c_name} {c_type}"))
                    
                    if 'technicians' in tables:
                        t_cols = [c['name'] for c in inspector.get_columns('technicians')]
                        tech_cols_to_add = [
                            ('skill_tags', 'VARCHAR(256) DEFAULT "空调,洗衣机,冰箱"'),
                            ('cert_title', 'VARCHAR(100) DEFAULT "持证家电维修高级工"'),
                            ('service_address', 'VARCHAR(200) DEFAULT "城市中心商圈"'),
                            ('service_radius_km', 'FLOAT DEFAULT 5.0'),
                            ('balance', 'FLOAT DEFAULT 0.0'),
                            ('is_online', 'BOOLEAN DEFAULT 1'),
                            ('years_of_exp', 'INTEGER DEFAULT 5'),
                            ('tools_checked', 'VARCHAR(256) DEFAULT "数字万用表,双表阀充氟表,高空防坠安全绳"'),
                            ('preferred_brands', 'VARCHAR(256) DEFAULT "格力,美的,海尔,西门子"'),
                            ('night_order_enabled', 'BOOLEAN DEFAULT 1'),
                            ('profile_completed', 'BOOLEAN DEFAULT 0'),
                        ]
                        for tc_name, tc_type in tech_cols_to_add:
                            if tc_name not in t_cols:
                                conn.execute(text(f"ALTER TABLE technicians ADD COLUMN {tc_name} {tc_type}"))

                    if 'parts' in tables:
                        p_cols = [c['name'] for c in inspector.get_columns('parts')]
                        if 'stock_quantity' not in p_cols:
                            conn.execute(text("ALTER TABLE parts ADD COLUMN stock_quantity INTEGER DEFAULT 100"))
                        if 'min_stock_alert' not in p_cols:
                            conn.execute(text("ALTER TABLE parts ADD COLUMN min_stock_alert INTEGER DEFAULT 10"))
                    
                    if 'order_parts' in tables:
                        op_cols = [c['name'] for c in inspector.get_columns('order_parts')]
                        if 'old_part_sn' not in op_cols:
                            conn.execute(text("ALTER TABLE order_parts ADD COLUMN old_part_sn VARCHAR(60)"))
                        if 'old_part_returned' not in op_cols:
                            conn.execute(text("ALTER TABLE order_parts ADD COLUMN old_part_returned BOOLEAN DEFAULT 0"))
                    conn.commit()
        except Exception as e:
            print("DB Migration notice:", e)
