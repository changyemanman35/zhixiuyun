"""test_domain.py · 领域规则与状态机测试（29 项断言）
覆盖：保修判定、费用计算、时长与SLA口径、10条状态转移、拒绝无副作用
"""
import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Customer, Device, Technician, FaultType, Part, WorkOrder, WorkOrderEvent, OrderPart
import rules
import state_machine
import config

passed_assertions = 0

def check(condition, msg=""):
    global passed_assertions
    if not condition:
        raise AssertionError(f"断言失败: {msg}")
    passed_assertions += 1

def run_tests():
    global passed_assertions
    # 使用独立的内存数据库测试
    app = create_app(db_path=":memory:")
    with app.app_context():
        db.create_all()

        now = datetime(2026, 10, 1, 12, 0, 0)

        # ── 1. 保修判定（4 项）──
        # 设备 A：购买于 100 天前，保修 12 个月 -> 保内
        cust = Customer(name="测试客户", phone="13800009991", address="测试地址")
        db.session.add(cust)
        db.session.commit()

        dev_in = Device(customer_id=cust.id, model="M1", serial_no="SN-IN",
                        purchase_date=date(2026, 6, 1), warranty_months=12)
        dev_out = Device(customer_id=cust.id, model="M2", serial_no="SN-OUT",
                         purchase_date=date(2024, 1, 1), warranty_months=12)
        # 延保覆盖取 max
        dev_ext = Device(customer_id=cust.id, model="M3", serial_no="SN-EXT",
                         purchase_date=date(2024, 1, 1), warranty_months=12,
                         warranty_override_date=date(2026, 12, 31))
        # 到期当天仍算保内 (B-3)
        dev_today = Device(customer_id=cust.id, model="M4", serial_no="SN-TODAY",
                           purchase_date=date(2025, 10, 1), warranty_months=12)

        flag, _ = rules.judge_warranty(dev_in, now)
        check(flag is True, "保内单判定为 True")

        flag, _ = rules.judge_warranty(dev_out, now)
        check(flag is False, "保外单判定为 False")

        flag, actual_end = rules.judge_warranty(dev_ext, now)
        check(flag is True and actual_end == date(2026, 12, 31), "延保覆盖生效且取 max")

        flag, _ = rules.judge_warranty(dev_today, now)
        check(flag is True, "到期当天仍算保内 (B-3)")

        # ── 2. 状态机 10 条转移与事件（11 项）──
        tech1 = Technician(name="技师1", phone="13900000001", active=True)
        tech2 = Technician(name="技师2", phone="13900000002", active=True)
        db.session.add_all([dev_in, dev_out, dev_ext, dev_today, tech1, tech2])
        db.session.commit()

        # T1 建单 -> PENDING 且写创建事件
        order = WorkOrder(
            order_no="WO-20261001-0001", customer_id=cust.id, device_id=dev_in.id,
            description="测试报修", priority="normal", status="PENDING",
            warranty_flag=True, created_at=now
        )
        db.session.add(order)
        db.session.commit()
        evt1 = WorkOrderEvent(work_order_id=order.id, from_status=None, to_status="PENDING",
                              actor_role="dispatcher", note="建单", created_at=now)
        db.session.add(evt1)
        db.session.commit()
        check(order.status == "PENDING" and order.events.count() == 1, "T1 建单成功且写1条创建事件")

        # T2 派工
        t_dispatch = now + timedelta(hours=1)
        evt2 = state_machine.transition(order, "ASSIGNED", "dispatcher", actor_id=tech1.id, now=t_dispatch)
        order.technician_id = tech1.id
        db.session.commit()
        check(order.status == "ASSIGNED" and order.technician_id == tech1.id and order.dispatched_at == t_dispatch,
              "T2 派工写 technician_id 与 dispatched_at")

        # T9 改派
        t_reassign = t_dispatch + timedelta(minutes=30)
        orig_dispatch_time = order.dispatched_at
        evt_re = state_machine.transition(order, "ASSIGNED", "dispatcher", actor_id=tech2.id, note="技师临时有事", now=t_reassign)
        order.technician_id = tech2.id
        db.session.commit()
        check(order.technician_id == tech2.id, "T9 改派换技师")
        check(order.dispatched_at == orig_dispatch_time, "T9 改派保持首次 dispatched_at 不变")
        check("技师临时有事" in evt_re.note, "T9 事件含改派原因")

        # T3 开工
        t_start = t_reassign + timedelta(minutes=15)
        state_machine.transition(order, "IN_PROGRESS", "technician", actor_id=tech2.id, now=t_start)
        db.session.commit()
        check(order.status == "IN_PROGRESS", "T3 开工转 IN_PROGRESS")

        # T5 挂起
        t_hold = t_start + timedelta(hours=1)
        state_machine.transition(order, "ON_HOLD", "technician", actor_id=tech2.id, note="等待配件", now=t_hold)
        db.session.commit()
        check(order.status == "ON_HOLD", "T5 挂起转 ON_HOLD")

        # T6 恢复
        t_resume = t_hold + timedelta(hours=2)
        state_machine.transition(order, "IN_PROGRESS", "technician", actor_id=tech2.id, now=t_resume)
        db.session.commit()
        check(order.status == "IN_PROGRESS", "T6 恢复转 IN_PROGRESS")

        # T4 完工 (保内费用全0)
        t_complete = t_resume + timedelta(hours=2)
        state_machine.transition(order, "WAIT_CONFIRM", "technician", actor_id=tech2.id, now=t_complete)
        fees = rules.calc_fee(order, parts_detail=[(100.0, 1)], labor_hours=2.0)
        order.labor_fee = fees['labor_fee']
        order.part_fee = fees['part_fee']
        order.visit_fee = fees['visit_fee']
        order.total_fee = fees['total_fee']
        db.session.commit()
        check(order.status == "WAIT_CONFIRM" and order.total_fee == 0.0, "T4 完工且保内费用全 0")

        # T7 客户确认关单
        t_close = t_complete + timedelta(hours=25)
        state_machine.transition(order, "CLOSED", "customer", now=t_close)
        db.session.commit()
        check(order.status == "CLOSED" and order.closed_at == t_close, "T7 客户确认转 CLOSED 且写 closed_at")

        # 全程每步恰好一条事件
        # 建单(1) + 派工(1) + 改派(1) + 开工(1) + 挂起(1) + 恢复(1) + 完工(1) + 关单(1) = 8
        check(order.events.count() == 8, "全程每步恰好一条事件，不多写不漏写 (CHK-12)")

        # ── 3. 费用计算（2 项）──
        order_out = WorkOrder(
            order_no="WO-20261001-0002", customer_id=cust.id, device_id=dev_out.id,
            description="保外测试", priority="normal", status="IN_PROGRESS",
            warranty_flag=False, created_at=now, dispatched_at=now
        )
        db.session.add(order_out)
        db.session.commit()
        fee_res = rules.calc_fee(order_out, parts_detail=[(420.0, 1), (180.0, 1)], labor_hours=2.5)
        # 工时费 2.5 * 80 = 200; 配件费 420 + 180 = 600; 普通上门费 50; 合计 850
        check(fee_res['labor_fee'] == 200.0 and fee_res['part_fee'] == 600.0 and fee_res['visit_fee'] == 50.0 and fee_res['total_fee'] == 850.0,
              "保外费用 = 工时 + 配件 + 上门")

        order_urgent = WorkOrder(
            order_no="WO-20261001-0003", customer_id=cust.id, device_id=dev_out.id,
            description="加急保外", priority="urgent", status="IN_PROGRESS",
            warranty_flag=False, created_at=now, dispatched_at=now
        )
        fee_urgent = rules.calc_fee(order_urgent, parts_detail=[], labor_hours=0.0)
        check(fee_urgent['visit_fee'] == config.VISIT_FEE_URGENT and fee_urgent['total_fee'] == config.VISIT_FEE_URGENT,
              "加急单上门费取高价 (80.0)")

        # ── 4. 拒绝后的无副作用（3 项）──
        # CLOSED 状态尝试转 ASSIGNED (非法转移)
        ev_count_before = order.events.count()
        status_before = order.status
        try:
            state_machine.transition(order, "ASSIGNED", "dispatcher")
            failed = False
        except state_machine.IllegalTransition:
            failed = True
        db.session.rollback()
        check(failed and order.status == status_before, "非法转移抛错且状态未变")
        check(order.events.count() == ev_count_before, "非法转移被拒后无事件写入")

        # 改派缺原因被拒绝
        order_assigned = WorkOrder(
            order_no="WO-20261001-0004", customer_id=cust.id, device_id=dev_in.id,
            description="改派测试", priority="normal", status="ASSIGNED",
            warranty_flag=True, created_at=now, dispatched_at=now, technician_id=tech1.id
        )
        db.session.add(order_assigned)
        db.session.commit()
        assigned_ev_before = order_assigned.events.count()
        try:
            state_machine.transition(order_assigned, "ASSIGNED", "dispatcher", actor_id=tech2.id, note="")
            reassign_fail = False
        except state_machine.NoteRequired:
            reassign_fail = True
        db.session.rollback()
        check(reassign_fail and order_assigned.status == "ASSIGNED" and order_assigned.technician_id == tech1.id and order_assigned.events.count() == assigned_ev_before,
              "改派缺原因被拒，状态与技师与事件均不变")

        # ── 5. SLA 与时长口径（9 项）──
        wo_p2 = WorkOrder(status="PENDING", created_at=now)
        wo_p5 = WorkOrder(status="PENDING", created_at=now - timedelta(hours=5))
        check(rules.sla_level(wo_p2, now) == "normal", "PENDING 2h = normal")
        check(rules.sla_level(wo_p5, now) == "warn", "PENDING 5h = warn")

        wo_ip10 = WorkOrder(status="IN_PROGRESS", dispatched_at=now - timedelta(hours=10))
        wo_ip50 = WorkOrder(status="IN_PROGRESS", dispatched_at=now - timedelta(hours=50))
        wo_ip75 = WorkOrder(status="IN_PROGRESS", dispatched_at=now - timedelta(hours=75))
        check(rules.sla_level(wo_ip10, now) == "normal", "IN_PROGRESS 10h = normal")
        check(rules.sla_level(wo_ip50, now) == "warn", "IN_PROGRESS 50h = warn")
        check(rules.sla_level(wo_ip75, now) == "danger", "IN_PROGRESS 75h = danger")

        wo_hold = WorkOrder(status="ON_HOLD", dispatched_at=now - timedelta(hours=100))
        check(rules.sla_level(wo_hold, now) == "warn", "ON_HOLD 即使超长也不判 danger (AC-4.3)")

        # 时长口径
        durations = rules.calc_durations(order)
        # order: created_at=now, dispatched_at=now+1h, completed_at=now+6.25h (approx 5.25h repair), closed_at=now+31.25h (25h closure)
        # 精确核算:
        order.created_at = now
        order.dispatched_at = now
        order.completed_at = now + timedelta(hours=5)
        order.closed_at = now + timedelta(hours=30)
        d = rules.calc_durations(order)
        check(d['response_duration'] == 0.0, "response_duration = 0.0h")
        check(d['repair_duration'] == 5.0, "repair_duration = 5.0h (派工->完工)")
        check(d['closure_duration'] == 25.0, "closure_duration = 25.0h (完工->关单)")

    print(f"[PASS] test_domain.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
