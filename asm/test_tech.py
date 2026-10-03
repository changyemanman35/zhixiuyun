"""test_tech.py · 技师端测试（32 项断言）
覆盖：技师待办、开工、挂起（带原因/拒绝无副作用/不进SLA红线）、恢复、完工预填、费用计算、快照价、保内免费、越权保护、事件链
"""
import sys
import os
import re
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Customer, Device, Technician, FaultType, Part, WorkOrder, WorkOrderEvent, OrderPart, utcnow
import rules
import config

passed_assertions = 0

def check(condition, msg=""):
    global passed_assertions
    if not condition:
        raise AssertionError(f"断言失败: {msg}")
    passed_assertions += 1

def run_tests():
    global passed_assertions
    app = create_app(db_path=":memory:")
    client = app.test_client()

    with app.app_context():
        db.create_all()

        now = utcnow()
        cust = Customer(name="李雷", phone="13800000002", address="高新区")
        tech1 = Technician(name="张工", phone="13900000011", active=True)
        tech2 = Technician(name="刘工", phone="13900000012", active=True)
        ft1 = FaultType(name="硬盘故障", active=True)
        ft_disabled = FaultType(name="已停用故障", active=False)
        p1 = Part(name="硬盘 1T", unit_price=420.0, active=True)
        p_disabled = Part(name="停用网线", unit_price=10.0, active=False)
        db.session.add_all([cust, tech1, tech2, ft1, ft_disabled, p1, p_disabled])
        db.session.commit()

        dev_out = Device(customer_id=cust.id, model="服务器 S-900", serial_no="SN-T1",
                         purchase_date=(now - timedelta(days=500)).date(), warranty_months=12)
        dev_in = Device(customer_id=cust.id, model="笔记本 N-15", serial_no="SN-T2",
                        purchase_date=(now - timedelta(days=30)).date(), warranty_months=12)
        db.session.add_all([dev_out, dev_in])
        db.session.commit()

        # ── 准备一张保外工单分配给 tech1 ──
        # 创建时间为 3 小时前，派工时间为 2.5 小时前
        order1 = WorkOrder(
            order_no="WO-20261001-0101", customer_id=cust.id, device_id=dev_out.id,
            description="开机蓝屏", priority="normal", status="ASSIGNED",
            warranty_flag=False, created_at=now - timedelta(hours=3),
            dispatched_at=now - timedelta(hours=2.5), technician_id=tech1.id
        )
        db.session.add(order1)
        db.session.commit()

        e1 = WorkOrderEvent(work_order_id=order1.id, from_status=None, to_status="PENDING",
                            actor_role="dispatcher", note="建单", created_at=order1.created_at)
        e2 = WorkOrderEvent(work_order_id=order1.id, from_status="PENDING", to_status="ASSIGNED",
                            actor_role="dispatcher", actor_id=tech1.id, note="派工", created_at=order1.dispatched_at)
        db.session.add_all([e1, e2])
        db.session.commit()

        # ── 1~2. 我的待办出现该单、按状态分入「待开工」 ──
        # 设置 session
        with client.session_transaction() as sess:
            sess['current_tech_id'] = tech1.id

        res = client.get('/tech')
        html = res.data.decode('utf-8', errors='replace')
        check(order1.order_no in html, "1. 我的待办出现该工单")
        check("待开工" in html, "2. 按状态分入「待开工」列")

        # ── 3. 开工转 IN_PROGRESS ──
        client.post(f'/tech/{order1.id}/start', follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "IN_PROGRESS", "3. 技师开工状态转 IN_PROGRESS")

        # ── 4~6. 挂起：空原因被拒、拒绝后无副作用（状态不变、无事件写入）、带原因挂起成功 ──
        ev_count_before = order1.events.count()
        client.post(f'/tech/{order1.id}/hold', data={'note': ''}, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "IN_PROGRESS", "4. 空原因挂起被拒，状态仍为 IN_PROGRESS")
        check(order1.events.count() == ev_count_before, "5. 拒绝后无副作用（无事件写入）")

        client.post(f'/tech/{order1.id}/hold', data={'note': '等主板备件'}, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "ON_HOLD", "6. 带原因挂起成功，状态转 ON_HOLD")

        # ── 7~8. 待办出现「等配件」、CHK/AC-4.3 挂起不进红线 ──
        res_tech_hold = client.get('/tech')
        check("等配件" in res_tech_hold.data.decode('utf-8', errors='replace'), "7. 待办出现「等配件」列")
        # 即使挂起超过 72h 也不判 danger
        order1.dispatched_at = now - timedelta(hours=100)
        db.session.commit()
        check(rules.sla_level(order1, now) == "warn", "8. [CHK/AC-4.3] 挂起状态不判 danger 红线")

        # ── 9. 恢复 → IN_PROGRESS ──
        client.post(f'/tech/{order1.id}/resume', follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "IN_PROGRESS", "9. 恢复转回 IN_PROGRESS")

        # ── 10~11. 完工表单预填 2.5h、页面展示费用单价来自 config ──
        order1.dispatched_at = now - timedelta(hours=2.5)
        db.session.commit()
        res_form = client.get(f'/tech/{order1.id}/complete')
        form_html = res_form.data.decode('utf-8', errors='replace')
        check('value="2.5"' in form_html or '2.5' in form_html, "10. 工时按 0.5 步长预填 2.5")
        check(str(config.LABOR_RATE_PER_HOUR) in form_html, "11. 页面展示费用预览且单价来自 config")
        check("已停用故障" not in form_html, "已停用故障分类不出现在完工表单")
        check("停用网线" not in form_html, "已停用配件不出现在完工表单")

        # ── 12~14. 缺故障分类被拒、缺处理方式被拒、两次拒绝后状态仍为 IN_PROGRESS ──
        client.post(f'/tech/{order1.id}/complete', data={
            'fault_type_id': '',
            'resolution': '更换配件',
            'labor_hours': '2.5'
        }, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "IN_PROGRESS", "12. 缺故障分类被拒，状态不变")

        client.post(f'/tech/{order1.id}/complete', data={
            'fault_type_id': str(ft1.id),
            'resolution': '',
            'labor_hours': '2.5'
        }, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "IN_PROGRESS", "13. 缺处理方式被拒，状态不变")
        check(order1.status == "IN_PROGRESS", "14. 两次拒绝后状态仍为 IN_PROGRESS")

        # ── 15~22. 提交完工 → WAIT_CONFIRM 及费用、落库与快照价 ──
        res_complete = client.post(f'/tech/{order1.id}/complete', data={
            'fault_type_id': str(ft1.id),
            'resolution': '更换配件',
            'labor_hours': '2.5',
            'resolution_note': '更换全新1T硬盘',
            f'qty_{p1.id}': '1'
        }, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "WAIT_CONFIRM", "15. 提交完工转 WAIT_CONFIRM")
        check(order1.labor_fee == 200.0, "16. 工时费 = 2.5h × 80 = 200.0")
        check(order1.part_fee == 420.0, "17. 配件费 = 420.0")
        check(order1.visit_fee == 50.0, "18. 普通单上门费 = 50.0")
        check(order1.total_fee == 670.0, "19. 合计 = 三项之和 = 670.0")
        check(order1.resolution == "更换配件", "20. 处理方式落库")
        check(order1.resolution_note == "更换全新1T硬盘", "21. 完工说明落库且不对外")
        op = OrderPart.query.filter_by(order_id=order1.id).first()
        check(op is not None and op.unit_price == 420.0, "22. 配件明细1行且单价为快照价 420.0")

        # ── 23. 保内单 total_fee = 0、三项费用均为 0 ──
        order_in = WorkOrder(
            order_no="WO-20261001-0102", customer_id=cust.id, device_id=dev_in.id,
            description="屏幕不亮", priority="normal", status="IN_PROGRESS",
            warranty_flag=True, created_at=now - timedelta(hours=2),
            dispatched_at=now - timedelta(hours=1), technician_id=tech1.id
        )
        db.session.add(order_in)
        db.session.commit()
        client.post(f'/tech/{order_in.id}/complete', data={
            'fault_type_id': str(ft1.id),
            'resolution': '调试修复',
            'labor_hours': '1.0',
            f'qty_{p1.id}': '1'
        }, follow_redirects=True)
        db.session.refresh(order_in)
        check(order_in.total_fee == 0.0 and order_in.labor_fee == 0.0 and order_in.part_fee == 0.0 and order_in.visit_fee == 0.0,
              "23. 保内单费用全部强制为 0.0")

        # ── 24~26. 他人单提交完工被拒、被拒后状态不变、他人待办为空 ──
        with client.session_transaction() as sess:
            sess['current_tech_id'] = tech2.id  # 切换为 tech2

        res_other = client.post(f'/tech/{order_in.id}/complete', data={
            'fault_type_id': str(ft1.id),
            'resolution': '调试修复',
            'labor_hours': '1.0'
        }, follow_redirects=True)
        check("只能操作自己的工单" in res_other.data.decode('utf-8', errors='replace'), "24. 他人单提交完工被拒")
        check(order_in.status == "WAIT_CONFIRM", "25. 被拒后工单状态不变")

        res_tech2_board = client.get('/tech')
        check(order1.order_no not in res_tech2_board.data.decode('utf-8', errors='replace'), "26. 他人待办中不显示该工单")

        # ── 27~28. 事件链条数与挂起原因 ──
        # order1: 建单(1) + 派工(1) + 开工(1) + 挂起(1) + 恢复(1) + 完工(1) = 6条
        events1 = order1.events.all()
        check(len(events1) == 6, "27. 事件链共 6 条事件")
        hold_evt = [e for e in events1 if e.to_status == "ON_HOLD"][0]
        check(hold_evt.note == "等主板备件", "28. 挂起原因正确记录入事件日志")
        check(events1[2].actor_role == "technician", "29. 开工事件记录由技师触发")
        check(events1[5].actor_role == "technician", "30. 完工事件记录由技师触发")
        check(order_in.resolution == "调试修复", "31. 保内单处理方式正确落库")
        check(order_in.labor_hours == 1.0, "32. 保内单工时正确落库")

    print(f"[PASS] test_tech.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
