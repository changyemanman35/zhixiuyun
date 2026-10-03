"""ASM 种子数据生成器 ── 28 张工单，覆盖全部 7 个状态
一切走真实规则（AC-8.2）：状态机转移、保修判定、费用计算
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone, date

# 确保能 import 项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from models import (db, Customer, Device, Technician, FaultType, Part,
                    WorkOrder, WorkOrderEvent, OrderPart, utcnow)
from state_machine import transition
import rules


# ── 固定随机种子，保证可复现 ──
SEED = config.BATCH_RNG_SEED


def _now_func():
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── 主数据定义 ──

CUSTOMERS_DATA = [
    {'name': '王强',  'phone': '13800001001', 'company': '明德科技',     'address': '济南市历下区经十路 256 号'},
    {'name': '李敏',  'phone': '13800001002', 'company': '锐创电子',     'address': '济南市市中区二环南路 128 号'},
    {'name': '赵磊',  'phone': '13800001003', 'company': '启航教育',     'address': '济南市槐荫区经四路 512 号'},
    {'name': '孙倩',  'phone': '13800001004', 'company': None,          'address': '济南市天桥区北园大街 300 号'},
    {'name': '周涛',  'phone': '13800001005', 'company': '汇通物流',     'address': '济南市章丘区明水大道 66 号'},
    {'name': '吴芳',  'phone': '13800001006', 'company': None,          'address': '济南市高新区舜华路 1008 号'},
]

TECHNICIANS_DATA = [
    {'name': '李海', 'phone': '13900001101', 'skill_tags': '服务器,存储,网络'},
    {'name': '王磊', 'phone': '13900001102', 'skill_tags': '打印机,投影仪,一体机'},
    {'name': '陈静', 'phone': '13900001103', 'skill_tags': '空调,电源'},
    {'name': '刘洋', 'phone': '13900001104', 'skill_tags': '笔记本,台式机,外设'},
]

FAULT_TYPES_DATA = [
    {'name': '硬盘故障', 'active': True},
    {'name': '卡纸',     'active': True},
    {'name': '电源故障', 'active': True},
    {'name': '散热不良', 'active': True},
    {'name': '系统崩溃', 'active': True},
    {'name': '网络中断', 'active': True},
    {'name': '镜头进灰', 'active': False},  # 停用项
]

PARTS_DATA = [
    {'name': '硬盘 1T',      'unit_price': 420.00, 'active': True},
    {'name': '电源模块',      'unit_price': 260.00, 'active': True},
    {'name': '内存条 8G',     'unit_price': 180.00, 'active': True},
    {'name': '散热风扇',      'unit_price': 90.00,  'active': True},
    {'name': '主板 X99',      'unit_price': 1200.00,'active': True},
    {'name': '网线 六类 30m', 'unit_price': 120.00, 'active': False},  # 停用
]


def _get_devices_data(now):
    """设备数据（购买日用相对偏移，保证任何日期运行都能演出同样的保修结论）"""
    today = now.date() if hasattr(now, 'date') else now
    return [
        # (客户索引, 型号, 序列号, 购买日偏移天, 保修月数, 延保覆盖偏移天, 演示意图)
        (0, '服务器 S-900',     'SN-88231A', -100, 12, None,   '保内'),
        (0, '磁盘阵列 A-16',   'SN-88232B', -500, 12, None,   '保外'),
        (1, '打印机 P-100',    'SN-77120C', -30,  12, None,   '保内'),
        (1, '投影仪 V-30',     'SN-55410D', -420, 12, None,   '保外'),
        (2, '教学一体机 T-86', 'SN-90311E', -200, 24, None,   '保内(24月)'),
        (2, '交换机 SW-24',    'SN-11009F', -700, 12, None,   '保外'),
        (3, '空调 K-200',      'SN-33902G', -366, 12, None,   '保修今天到期→保内(B-3)'),
        (4, '笔记本 N-15',     'SN-62045H', -500, 12, 180,    '过保但延保→保内(WR-3)'),
        (4, '条码扫描枪 B-7',  None,        -60,  12, None,   '保内(无序列号)'),
        (5, '台式机 D-500',    'SN-47120J', -800, 12, None,   '保外'),
    ]


# ── 工单计划表（28 张）──
# (设备索引, 目标状态, 派工延迟h, 维修时长h, 确认延迟h, 故障索引, 配件[(索引,数量)], 优先级, 备注, 改派标记, 月份标记)

ORDER_PLANS = [
    # ── 本月批（16 张）──
    (0, 'CLOSED',       2,  5,   3, 0, [(0,1)],         'normal',  '',              False, 'this'),
    (2, 'CLOSED',       1,  8,   2, 1, [],               'normal',  '',              False, 'this'),
    (1, 'CLOSED',       3,  12,  4, 0, [(0,2),(2,1)],   'normal',  '',              False, 'this'),
    (7, 'WAIT_CONFIRM', 2,  7,   0, 2, [(1,1)],         'normal',  '',              False, 'this'),
    (4, 'CLOSED',       2,  9,   5, 4, [],               'normal',  '',              False, 'this'),
    (8, 'CLOSED',       2,  6,   2, 1, [],               'normal',  '',              False, 'this'),
    (6, 'WAIT_CONFIRM', 1,  5,   0, 3, [],               'normal',  '',              False, 'this'),
    (9, 'CLOSED',       3,  15,  4, 3, [(3,2)],         'normal',  '',              False, 'this'),
    (3, 'CLOSED',       5,  12,  3, 2, [(1,1)],         'normal',  '★响应5h>4h→超时', False, 'this'),
    (0, 'IN_PROGRESS',  1,  0,   0, -1,[],               'normal',  '在途',          False, 'this'),
    (4, 'IN_PROGRESS',  2,  0,   0, -1,[],               'normal',  '在途',          False, 'this'),
    (2, 'ON_HOLD',      1,  0,   0, -1,[],               'normal',  '等厂家发主板',  False, 'this'),
    (3, 'ASSIGNED',     1,  0,   0, -1,[],               'urgent',  '加急未开工',    False, 'this'),
    (5, 'PENDING',      0,  0,   0, -1,[],               'normal',  '未派工',        False, 'this'),
    (9, 'CANCELLED',    0,  0,   0, -1,[],               'normal',  '客户自行解决',  False, 'this'),
    (0, 'CLOSED',       1,  6,   2, 0, [(0,1)],         'normal',  '★改派',         True,  'this'),

    # ── 上月批（12 张）──
    (1, 'CLOSED',       2,  10,  3, 0, [(0,1),(3,1)],   'normal',  '',              False, 'last'),
    (3, 'CLOSED',       1,  7,   2, 2, [(1,1)],         'normal',  '',              False, 'last'),
    (5, 'CLOSED',       6,  30,  4, 5, [(2,2)],         'urgent',  '★响应6h>4h→超时', False, 'last'),
    (9, 'CLOSED',       2,  14,  5, 4, [],               'normal',  '',              False, 'last'),
    (0, 'CLOSED',       3,  55,  2, 0, [(4,1)],         'normal',  '★维修55h>48h→超时', False, 'last'),
    (4, 'CLOSED',       1,  9,   3, 1, [],               'normal',  '',              False, 'last'),
    (6, 'WAIT_CONFIRM', 2,  8,   0, 3, [],               'normal',  '久未确认→黄',    False, 'last'),
    (7, 'WAIT_CONFIRM', 1,  6,   0, 2, [(1,1)],         'normal',  '久未确认→黄',    False, 'last'),
    (8, 'IN_PROGRESS',  1,  0,   0, -1,[],               'normal',  '久未完工→红',    False, 'last'),
    (2, 'ON_HOLD',      2,  0,   0, -1,[],               'normal',  '配件缺货',      False, 'last'),
    (5, 'PENDING',      0,  0,   0, -1,[],               'normal',  '久未派工→黄',    False, 'last'),
    (0, 'CANCELLED',    1,  0,   0, -1,[],               'normal',  '过保客户放弃',  False, 'last'),
]


def _ensure_master_data(now):
    """确保主数据存在（幂等：按唯一键查重复用）"""
    customers = []
    for c_data in CUSTOMERS_DATA:
        c = Customer.query.filter_by(phone=c_data['phone']).first()
        if not c:
            c = Customer(**c_data, created_at=now)
            db.session.add(c)
            db.session.flush()
        customers.append(c)

    devices_def = _get_devices_data(now)
    devices = []
    for ci, model, sn, day_offset, wm, ext_offset, _ in devices_def:
        purchase = (now.date() if hasattr(now, 'date') else now) + timedelta(days=day_offset)
        override = None
        if ext_offset is not None:
            override = (now.date() if hasattr(now, 'date') else now) + timedelta(days=ext_offset)

        if sn:
            d = Device.query.filter_by(serial_no=sn).first()
        else:
            # 无序列号：按客户+型号去重（M6-B3）
            d = Device.query.filter_by(customer_id=customers[ci].id, model=model).first()

        if not d:
            d = Device(
                customer_id=customers[ci].id, model=model, serial_no=sn,
                purchase_date=purchase, warranty_months=wm,
                warranty_override_date=override, created_at=now,
            )
            db.session.add(d)
            db.session.flush()
        devices.append(d)

    techs = []
    for t_data in TECHNICIANS_DATA:
        t = Technician.query.filter_by(name=t_data['name']).first()
        if not t:
            t = Technician(**t_data, created_at=now)
            db.session.add(t)
            db.session.flush()
        techs.append(t)

    faults = []
    for f_data in FAULT_TYPES_DATA:
        f = FaultType.query.filter_by(name=f_data['name']).first()
        if not f:
            f = FaultType(**f_data)
            db.session.add(f)
            db.session.flush()
        else:
            f.active = f_data['active']
        faults.append(f)

    parts = []
    for p_data in PARTS_DATA:
        p = Part.query.filter_by(name=p_data['name']).first()
        if not p:
            p = Part(**p_data, stock_quantity=100, min_stock_alert=10)
            db.session.add(p)
            db.session.flush()
        else:
            p.unit_price = p_data['unit_price']
            p.active = p_data['active']
            if not p.stock_quantity:
                p.stock_quantity = 100
            if not p.min_stock_alert:
                p.min_stock_alert = 10
        parts.append(p)

    # 初始化官方授权服务网点 (spec.md 2.3.0 F2)
    from models import ServiceStation
    STATIONS_DATA = [
        {
            'name': '海尔官方华南旗舰售后服务中心',
            'city': '深圳市',
            'district': '南山区',
            'address': '深圳市南山区科技园高新南七道 18 号创新大厦首层',
            'phone': '0755-88886666',
            'business_hours': '周一至周日 08:30-18:00',
            'coverage_area': '南山区、福田区、宝安区'
        },
        {
            'name': '苹果官方直营服务中心 (益田假日广场天才吧)',
            'city': '深圳市',
            'district': '南山区',
            'address': '深圳市南山区深南大道 9028 号益田假日广场 B1 层',
            'phone': '0755-86289000',
            'business_hours': '周一至周日 10:00-22:00',
            'coverage_area': '全深圳全品类支持送修与上门'
        },
        {
            'name': '官方华北核心售后服务站 (济南高新中心)',
            'city': '济南市',
            'district': '高新区',
            'address': '济南市高新区舜华路 1008 号科技金融大厦 B座 102室',
            'phone': '0531-86001234',
            'business_hours': '周一至周六 09:00-17:30',
            'coverage_area': '历下区、高新区、历城区'
        },
        {
            'name': '官方华东综合售后服务中心 (上海陆家嘴站)',
            'city': '上海市',
            'district': '浦东新区',
            'address': '上海市浦东新区世纪大道 8 号国金中心 2 层',
            'phone': '021-68889900',
            'business_hours': '周一至周日 09:00-20:00',
            'coverage_area': '浦东新区、黄浦区、徐汇区'
        }
    ]
    for s_info in STATIONS_DATA:
        s = ServiceStation.query.filter_by(name=s_info['name']).first()
        if not s:
            s = ServiceStation(**s_info, active=True, created_at=now)
            db.session.add(s)

    # 初始化默认系统演示账号 (admin / tech1 / cust1)
    from models import User
    default_users = [
        {'username': 'admin', 'role': 'dispatcher', 'name': '系统调度管理员', 'phone': '13800000000', 'related_id': None},
        {'username': 'tech1', 'role': 'technician', 'name': techs[0].name, 'phone': techs[0].phone, 'related_id': techs[0].id},
        {'username': 'cust1', 'role': 'customer', 'name': customers[0].name, 'phone': customers[0].phone, 'related_id': customers[0].id}
    ]
    for u_info in default_users:
        u = User.query.filter_by(username=u_info['username']).first()
        if not u:
            u = User(**u_info)
            u.set_password('123456')
            db.session.add(u)

    db.session.commit()
    return customers, devices, techs, faults, parts


def _assign_technician(rng, device, techs):
    """按设备类型分配技师"""
    model_lower = device.model.lower()
    if '服务器' in model_lower or '磁盘' in model_lower or '交换机' in model_lower:
        return techs[0]  # 李海
    elif '打印机' in model_lower or '投影仪' in model_lower or '一体机' in model_lower:
        return techs[1]  # 王磊
    elif '空调' in model_lower:
        return techs[2]  # 陈静
    else:
        return techs[3]  # 刘洋


def generate_demo_data(now=None, mode='append'):
    """生成演示数据

    Args:
        now: 当前时刻（默认 utcnow()）
        mode: 'append' 追加 / 'reset' 先清空再生成
    """
    if now is None:
        now = _now_func()

    rng = random.Random(SEED)

    if mode == 'reset':
        clear_demo_data()

    # 确保主数据
    customers, devices, techs, faults, parts = _ensure_master_data(now)

    # 月份基准
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if this_month_start.month == 1:
        last_month_start = this_month_start.replace(year=this_month_start.year - 1, month=12)
    else:
        last_month_start = this_month_start.replace(month=this_month_start.month - 1)

    orders_created = 0

    for plan_idx, plan in enumerate(ORDER_PLANS):
        dev_idx, target, dispatch_h, repair_h, confirm_h, fault_idx, parts_spec, priority, note, is_reassign, month_tag = plan

        device = devices[dev_idx]
        customer = device.customer

        # 时间布局
        if month_tag == 'this':
            month_start = this_month_start
            month_end = now
        else:
            month_start = last_month_start
            month_end = this_month_start

        # 在途单锚点钉在"现在前 4~132 小时"（SEED-1）
        is_in_transit = target in ('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD', 'WAIT_CONFIRM') and target != 'CLOSED' and target != 'CANCELLED'

        if is_in_transit and target != 'CLOSED':
            # 在途单：最后一个事件在 now 前 4~132 小时
            anchor_hours = rng.uniform(4, 132)
            total_hours = dispatch_h + repair_h + confirm_h
            created_at = now - timedelta(hours=anchor_hours + total_hours + rng.uniform(0.5, 2))
        else:
            # 已关闭/已取消：均匀分布在月份区间
            total_hours = dispatch_h + repair_h + confirm_h
            span = (month_end - month_start).total_seconds()
            min_span = total_hours * 3600 + 3600
            if span <= min_span:
                offset_s = 0
            else:
                offset_s = rng.uniform(0, span - min_span)
            created_at = month_start + timedelta(seconds=offset_s)

        # 确保不超过 now
        if created_at >= now:
            created_at = now - timedelta(hours=total_hours + 2)

        # 保修判定（走真实规则）
        warranty_flag, actual_end = rules.judge_warranty(device, created_at)

        # 工单号（走真实规则）
        order_no = rules.generate_order_no(created_at, db.session)

        order = WorkOrder(
            order_no=order_no,
            customer_id=customer.id,
            device_id=device.id,
            description=f'[演示] {device.model} 报修' + (f' - {note}' if note else ''),
            priority=priority,
            status='PENDING',
            created_at=created_at,
            warranty_flag=warranty_flag,
            is_demo=True,
        )
        db.session.add(order)
        db.session.flush()

        # 创建事件
        evt_create = WorkOrderEvent(
            work_order_id=order.id, from_status=None, to_status='PENDING',
            actor_role='dispatcher', note='建单', created_at=created_at,
        )
        db.session.add(evt_create)

        t_cursor = created_at

        # CANCELLED（可能从 PENDING 或 ASSIGNED 取消）
        if target == 'CANCELLED':
            if dispatch_h > 0:
                # 先派工再取消
                tech = _assign_technician(rng, device, techs)
                t_dispatch = t_cursor + timedelta(hours=dispatch_h)
                order.technician_id = tech.id
                order.dispatched_at = t_dispatch
                order.status = 'ASSIGNED'
                db.session.add(WorkOrderEvent(
                    work_order_id=order.id, from_status='PENDING', to_status='ASSIGNED',
                    actor_role='dispatcher', actor_id=tech.id,
                    note=f'派工给{tech.name}', created_at=t_dispatch,
                ))
                t_cursor = t_dispatch + timedelta(minutes=rng.randint(30, 120))
                # 取消
                order.status = 'CANCELLED'
                db.session.add(WorkOrderEvent(
                    work_order_id=order.id, from_status='ASSIGNED', to_status='CANCELLED',
                    actor_role='dispatcher', note=note or '客户取消', created_at=t_cursor,
                ))
            else:
                t_cursor = t_cursor + timedelta(minutes=rng.randint(10, 60))
                order.status = 'CANCELLED'
                db.session.add(WorkOrderEvent(
                    work_order_id=order.id, from_status='PENDING', to_status='CANCELLED',
                    actor_role='dispatcher', note=note or '客户取消', created_at=t_cursor,
                ))
            db.session.flush()
            orders_created += 1
            continue

        # PENDING（不派工）
        if target == 'PENDING':
            db.session.flush()
            orders_created += 1
            continue

        # 派工
        tech = _assign_technician(rng, device, techs)
        t_dispatch = t_cursor + timedelta(hours=dispatch_h)
        order.technician_id = tech.id
        order.dispatched_at = t_dispatch
        order.status = 'ASSIGNED'
        db.session.add(WorkOrderEvent(
            work_order_id=order.id, from_status='PENDING', to_status='ASSIGNED',
            actor_role='dispatcher', actor_id=tech.id,
            note=f'派工给{tech.name}', created_at=t_dispatch,
        ))
        t_cursor = t_dispatch

        # 改派
        if is_reassign:
            t_reassign = t_cursor + timedelta(minutes=30)
            # 选另一个技师
            other_techs = [t for t in techs if t.id != tech.id and t.active]
            new_tech = rng.choice(other_techs) if other_techs else tech
            order.technician_id = new_tech.id
            # dispatched_at 不变（铁律4）
            db.session.add(WorkOrderEvent(
                work_order_id=order.id, from_status='ASSIGNED', to_status='ASSIGNED',
                actor_role='dispatcher', actor_id=new_tech.id,
                note=f'原技师{tech.name}在外地，改派{new_tech.name}',
                created_at=t_reassign,
            ))
            tech = new_tech
            t_cursor = t_reassign

        if target == 'ASSIGNED':
            db.session.flush()
            orders_created += 1
            continue

        # 开工
        t_start = t_cursor + timedelta(minutes=rng.randint(10, 60))
        order.status = 'IN_PROGRESS'
        db.session.add(WorkOrderEvent(
            work_order_id=order.id, from_status='ASSIGNED', to_status='IN_PROGRESS',
            actor_role='technician', actor_id=tech.id,
            note='开始维修', created_at=t_start,
        ))
        t_cursor = t_start

        # ON_HOLD（挂起等配件，不完工）
        if target == 'ON_HOLD':
            t_hold = t_cursor + timedelta(hours=rng.uniform(1, 3))
            order.status = 'ON_HOLD'
            db.session.add(WorkOrderEvent(
                work_order_id=order.id, from_status='IN_PROGRESS', to_status='ON_HOLD',
                actor_role='technician', actor_id=tech.id,
                note=note or '等配件到货', created_at=t_hold,
            ))
            db.session.flush()
            orders_created += 1
            continue

        if target == 'IN_PROGRESS':
            # 在途，不继续
            db.session.flush()
            orders_created += 1
            continue

        # 完工
        labor_hours = round(repair_h * rng.uniform(0.8, 1.0), 1)
        labor_hours = max(0.5, min(24.0, labor_hours))
        t_complete = t_cursor + timedelta(hours=repair_h)

        # 设置故障类型和处理方式
        if fault_idx >= 0:
            order.fault_type_id = faults[fault_idx].id
        order.resolution = rng.choice(config.RESOLUTIONS)
        order.labor_hours = labor_hours

        # 配件明细（快照价）
        parts_detail = []
        for p_idx, qty in parts_spec:
            part = parts[p_idx]
            op = OrderPart(
                order_id=order.id, part_id=part.id,
                quantity=qty, unit_price=part.unit_price,
            )
            db.session.add(op)
            parts_detail.append((part.unit_price, qty))

        # 费用计算（走真实规则）
        fees = rules.calc_fee(order, parts_detail, labor_hours)
        order.labor_fee = fees['labor_fee']
        order.part_fee = fees['part_fee']
        order.visit_fee = fees['visit_fee']
        order.total_fee = fees['total_fee']

        order.completed_at = t_complete
        order.status = 'WAIT_CONFIRM'
        db.session.add(WorkOrderEvent(
            work_order_id=order.id, from_status='IN_PROGRESS', to_status='WAIT_CONFIRM',
            actor_role='technician', actor_id=tech.id,
            note='维修完成', created_at=t_complete,
        ))
        t_cursor = t_complete

        if target == 'WAIT_CONFIRM':
            db.session.flush()
            orders_created += 1
            continue

        # 关单
        t_close = t_cursor + timedelta(hours=confirm_h)
        order.closed_at = t_close
        order.status = 'CLOSED'
        db.session.add(WorkOrderEvent(
            work_order_id=order.id, from_status='WAIT_CONFIRM', to_status='CLOSED',
            actor_role='customer', note='客户确认', created_at=t_close,
        ))
        db.session.flush()
        orders_created += 1

    db.session.commit()
    return orders_created


def clear_demo_data():
    """清空演示数据（只删 is_demo=True 的工单，主数据保留）（SEED-2）"""
    demo_orders = WorkOrder.query.filter_by(is_demo=True).all()
    for order in demo_orders:
        # 删配件明细
        OrderPart.query.filter_by(order_id=order.id).delete()
        # 删事件
        WorkOrderEvent.query.filter_by(work_order_id=order.id).delete()
        # 删工单
        db.session.delete(order)
    db.session.commit()
    db.session.expunge_all()
    return len(demo_orders)


def get_demo_stats():
    """获取演示数据统计"""
    demo_orders = WorkOrder.query.filter_by(is_demo=True).all()
    total = len(demo_orders)

    status_dist = {}
    for s in config.STATUSES:
        count = sum(1 for o in demo_orders if o.status == s)
        if count > 0:
            status_dist[s] = count

    # 超时关闭单
    late_closed = 0
    for o in demo_orders:
        if o.status == 'CLOSED':
            result = rules.is_on_time(o)
            if result is False:
                late_closed += 1

    # 客户查询凭证（找一张 WAIT_CONFIRM 的单）
    query_order = None
    for o in demo_orders:
        if o.status == 'WAIT_CONFIRM':
            query_order = o
            break
    if not query_order:
        for o in demo_orders:
            if o.status == 'CLOSED':
                query_order = o
                break

    query_credential = None
    if query_order:
        customer = db.session.get(Customer, query_order.customer_id)
        query_credential = {
            'order_no': query_order.order_no,
            'phone': customer.phone,
        }

    return {
        'total': total,
        'status_dist': status_dist,
        'late_closed': late_closed,
        'statuses_covered': len(status_dist),
        'query_credential': query_credential,
    }


def print_stats():
    """打印统计信息"""
    stats = get_demo_stats()
    print(f'\n演示工单 {stats["total"]} 张 · 覆盖 {stats["statuses_covered"]}/7 个状态')
    for s, c in stats['status_dist'].items():
        label = config.STATUS_LABELS.get(s, s)
        print(f'  {label}({s}) {c}')
    print(f'超时关闭单 {stats["late_closed"]} 张（AC-8.1 要求 ≥2）')
    if stats['query_credential']:
        cred = stats['query_credential']
        print(f'客户查询演示：工单号 {cred["order_no"]} + 手机号 {cred["phone"]}')
    print()


# ── CLI 入口 ──
if __name__ == '__main__':
    from app import create_app
    app = create_app()

    with app.app_context():
        if '--reset' in sys.argv:
            print('清空演示数据...')
            n = clear_demo_data()
            print(f'已清空 {n} 张演示工单')
            print('重新生成...')
            count = generate_demo_data(mode='reset')
            print(f'已生成 {count} 张演示工单')
            print_stats()

        elif '--append' in sys.argv:
            print('追加演示数据...')
            count = generate_demo_data(mode='append')
            print(f'已追加 {count} 张演示工单')
            print_stats()

        elif '--stats' in sys.argv:
            print_stats()

        else:
            # 默认：检查是否有数据，有则提示，无则生成
            from models import WorkOrder
            existing = WorkOrder.query.filter_by(is_demo=True).count()
            if existing > 0:
                print(f'已有 {existing} 张演示工单。')
                print('使用 --reset 清空重建，--append 追加，--stats 查看统计')
            else:
                print('生成演示数据...')
                count = generate_demo_data()
                print(f'已生成 {count} 张演示工单')
                print_stats()
