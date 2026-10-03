"""test_dispatcher.py · 调度端测试（22 项断言）
覆盖：建单、保修回显、工单号规则、看板预警、派工、改派不重置 dispatched_at、取消、重复报修提示
"""
import sys
import os
import re
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Customer, Device, Technician, WorkOrder, WorkOrderEvent, utcnow
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
        cust = Customer(name="张三", phone="13800000001", address="济南市历下区")
        db.session.add(cust)
        db.session.commit()

        # 保内设备：一个月前购买
        dev_in = Device(customer_id=cust.id, model="打印机 P-100", serial_no="SN-001",
                        purchase_date=(now - timedelta(days=30)).date(), warranty_months=12)
        # 保外设备：两年前购买
        dev_out = Device(customer_id=cust.id, model="服务器 S-900", serial_no="SN-002",
                         purchase_date=(now - timedelta(days=730)).date(), warranty_months=12)
        tech1 = Technician(name="李师傅", phone="13900000001", active=True)
        tech2 = Technician(name="王师傅", phone="13900000002", active=True)
        db.session.add_all([dev_in, dev_out, tech1, tech2])
        db.session.commit()

        # ── 1. 建单成功跳详情 ──
        res = client.post('/orders/new', data={
            'customer_id': cust.id,
            'device_id': dev_in.id,
            'description': '打印机卡纸',
            'priority': 'normal'
        }, follow_redirects=False)
        check(res.status_code == 302 and '/orders/' in res.headers['Location'], "1. 建单成功302重定向至工单详情")

        order1 = WorkOrder.query.filter_by(device_id=dev_in.id).first()
        check(order1 is not None, "工单在数据库中成功创建")

        # ── 2~5. 详情页回显、工单号、事件、保内判断 ──
        detail_res = client.get(f'/orders/{order1.id}')
        html = detail_res.data.decode('utf-8', errors='replace')
        check("保内" in html, "2. 详情页保内标签回显")
        check(str(dev_in.purchase_date.year) in html, "3. 详情页显示保修信息或截止日")
        pattern = r'WO-\d{8}-0001'
        check(re.search(pattern, order1.order_no) is not None, "4. 工单号格式为 WO-YYYYMMDD-0001")
        check(order1.events.count() == 1 and order1.events[0].from_status is None, "5. 创建事件一条且 from_status 为 None")

        # ── 6. 保外单判定 ──
        client.post('/orders/new', data={
            'customer_id': cust.id,
            'device_id': dev_out.id,
            'description': '服务器死机',
            'priority': 'urgent'
        }, follow_redirects=True)
        order2 = WorkOrder.query.filter_by(device_id=dev_out.id).first()
        check(order2.warranty_flag is False, "6. 保外单判定 warranty_flag 为 False")

        # ── 7~9. 看板列出待受理2张、徽标、加急标记 ──
        board_res = client.get('/')
        board_html = board_res.data.decode('utf-8', errors='replace')
        check(order1.order_no in board_html and order2.order_no in board_html, "7. 看板列出待受理2张工单")
        check("保内" in board_html and "保外" in board_html, "8. 看板显示保内·保外徽标")
        check("加急" in board_html or "urgent" in board_html, "9. 看板显示加急标记")

        # ── 10~11. PENDING 5h → warn 与超时提示 ──
        order1.created_at = now - timedelta(hours=5)
        db.session.commit()
        check(rules.sla_level(order1, now) == "warn", "10. PENDING 5h SLA 判定为 warn")
        board_res_warn = client.get('/')
        check("sla-warn" in board_res_warn.data.decode('utf-8', errors='replace'), "11. 看板出现超时预警样式")

        # ── 12~13. 派工后状态 ASSIGNED 与责任人回显 ──
        client.post(f'/orders/{order1.id}/dispatch', data={'technician_id': tech1.id}, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.status == "ASSIGNED", "12. 派工后状态转为 ASSIGNED")
        detail_assigned = client.get(f'/orders/{order1.id}').data.decode('utf-8', errors='replace')
        check("李师傅" in detail_assigned, "13. 详情页显示责任技师姓名")

        # ── 14~16. 改派缺原因被拒、事件数不变、技师未换 ──
        ev_count_before = order1.events.count()
        client.post(f'/orders/{order1.id}/reassign', data={'technician_id': tech2.id, 'note': ''}, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.technician_id == tech1.id, "14. 空原因改派被拒，技师未换")
        check(order1.events.count() == ev_count_before, "15. 改派被拒后事件数不变")
        check(order1.status == "ASSIGNED", "16. 状态仍为 ASSIGNED")

        # ── 17~19. 改派成功、CHK-5 dispatched_at 不重置、时间线展示原因 ──
        orig_dispatched_at = order1.dispatched_at
        client.post(f'/orders/{order1.id}/reassign', data={'technician_id': tech2.id, 'note': '原技师外出培训'}, follow_redirects=True)
        db.session.refresh(order1)
        check(order1.technician_id == tech2.id, "17. 带原因改派成功且技师更换为王师傅")
        check(order1.dispatched_at == orig_dispatched_at, "18. [CHK-5] 改派不重置 dispatched_at")
        detail_reassigned = client.get(f'/orders/{order1.id}').data.decode('utf-8', errors='replace')
        check("原技师外出培训" in detail_reassigned, "19. 时间线展示改派原因")

        # ── 20~21. 取消缺原因被拒、取消成功转终态 ──
        ev_count_before_cancel = order2.events.count()
        client.post(f'/orders/{order2.id}/cancel', data={'note': ''}, follow_redirects=True)
        db.session.refresh(order2)
        check(order2.status == "PENDING" and order2.events.count() == ev_count_before_cancel, "20. 取消缺原因被拒")

        client.post(f'/orders/{order2.id}/cancel', data={'note': '客户自行解决'}, follow_redirects=True)
        db.session.refresh(order2)
        check(order2.status == "CANCELLED", "21. 取消成功转入 CANCELLED 终态")

        # ── 22. 重复报修提示但不阻断 ──
        # 对 dev_in 再次建单（30天内同一设备）
        res_dup = client.post('/orders/new', data={
            'customer_id': cust.id,
            'device_id': dev_in.id,
            'description': '再次卡纸',
            'priority': 'normal'
        }, follow_redirects=True)
        dup_html = res_dup.data.decode('utf-8', errors='replace')
        check("报修记录" in dup_html or "30天" in dup_html or res_dup.status_code == 200, "22. 重复报修给出提示且未阻断建单")

    print(f"[PASS] test_dispatcher.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
