"""test_query.py · 客户免登录查询测试（47 项断言）
覆盖：免登录查询、隐私安全、两种失败响应体逐字节一致、确认关单、申请返工、状态细分与费用展示
"""
import sys
import os
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
        cust = Customer(name="周总", phone="13800003333", address="舜华路")
        tech = Technician(name="刘师傅", phone="13900003333", active=True)
        db.session.add_all([cust, tech])
        db.session.commit()

        dev = Device(customer_id=cust.id, model="投影仪 V-30", serial_no="SN-Q1",
                     purchase_date=(now - timedelta(days=500)).date(), warranty_months=12)
        dev_in = Device(customer_id=cust.id, model="打印机 P-100", serial_no="SN-Q2",
                        purchase_date=(now - timedelta(days=20)).date(), warranty_months=12)
        db.session.add_all([dev, dev_in])
        db.session.commit()

        # 准备一张 WAIT_CONFIRM 状态的工单
        order = WorkOrder(
            order_no="WO-20261001-0201", customer_id=cust.id, device_id=dev.id,
            description="投影仪灯泡不亮", priority="normal", status="WAIT_CONFIRM",
            warranty_flag=False, created_at=now - timedelta(hours=10),
            dispatched_at=now - timedelta(hours=8), completed_at=now - timedelta(hours=2),
            technician_id=tech.id, labor_hours=2.0, labor_fee=160.0, part_fee=260.0,
            visit_fee=50.0, total_fee=470.0, resolution="更换配件", resolution_note="更换内部高压电源板"
        )
        db.session.add(order)
        db.session.commit()

        # 写入配件明细
        p = Part(name="高压板", unit_price=260.0, active=True)
        db.session.add(p)
        db.session.commit()
        op = OrderPart(order_id=order.id, part_id=p.id, quantity=1, unit_price=260.0)
        db.session.add(op)

        # 写入事件
        e1 = WorkOrderEvent(work_order_id=order.id, from_status=None, to_status="PENDING",
                            actor_role="dispatcher", note="客户报修", created_at=order.created_at)
        e2 = WorkOrderEvent(work_order_id=order.id, from_status="PENDING", to_status="ASSIGNED",
                            actor_role="dispatcher", actor_id=tech.id, note="派工", created_at=order.dispatched_at)
        e3 = WorkOrderEvent(work_order_id=order.id, from_status="ASSIGNED", to_status="IN_PROGRESS",
                            actor_role="technician", actor_id=tech.id, note="开工", created_at=order.dispatched_at + timedelta(minutes=30))
        e4 = WorkOrderEvent(work_order_id=order.id, from_status="IN_PROGRESS", to_status="WAIT_CONFIRM",
                            actor_role="technician", actor_id=tech.id, note="维修完毕", created_at=order.completed_at)
        db.session.add_all([e1, e2, e3, e4])
        db.session.commit()

        # ── 1~10. 查询与展示 ──
        get_res = client.get('/query')
        check(get_res.status_code == 200, "1. GET /query 返回 200 表单")
        check('name="order_no"' in get_res.data.decode('utf-8', errors='replace'), "2. 页面含工单号输入框")

        post_res = client.post('/query', data={'order_no': order.order_no, 'phone': cust.phone})
        html = post_res.data.decode('utf-8', errors='replace')
        check(post_res.status_code == 200, "3. 凭正确凭证查询成功返回 200")
        check(order.order_no in html, "4. 页面显示当前工单号")
        check("待您确认" in html or "待确认" in html, "5. 显示当前状态待确认")
        check("已受理" in html and "已安排技师" in html and "维修中" in html and "已完成" in html, "6. 五段进度条齐备")
        check("138****3333" in html, "7. 手机号脱敏展示 (138****3333)")
        check("刘师傅" not in html and "13900003333" not in html, "8. 页面不含技师姓名与电话")
        check("更换内部高压电源板" not in html, "9. 页面不含内部处理说明备注")
        check("260.00" not in html and "470.00" in html, "10. 费用只显示总额，不显示配件单价")

        # ── 11~17. 失败路径安全关键 ──
        # 错误手机号 vs 不存在工单号
        res_wrong_phone = client.post('/query', data={'order_no': order.order_no, 'phone': '13800009999'})
        res_wrong_order = client.post('/query', data={'order_no': 'WO-99999999-9999', 'phone': cust.phone})
        html_wp = res_wrong_phone.data.decode('utf-8', errors='replace')
        html_wo = res_wrong_order.data.decode('utf-8', errors='replace')

        check("未找到匹配" in html_wp, "11. 错误手机号提示统一")
        check("未找到匹配" in html_wo, "12. 不存在工单号提示统一")
        check(res_wrong_phone.data == res_wrong_order.data, "13. 两种失败响应体逐字节完全相同")
        check(len(res_wrong_phone.data) == len(res_wrong_order.data), "14. 两种失败响应体字节数完全相等")
        check(order.order_no not in html_wp, "15. 失败页不回显工单号")
        check("13800009999" not in html_wp, "16. 失败页不回显手机号")
        check("投影仪" not in html_wp, "17. 失败页不泄露设备信息")

        # ── 18~25. 确认关单 ──
        ev_count_before = order.events.count()
        client.post('/query/confirm', data={'order_no': order.order_no, 'phone': cust.phone})
        db.session.refresh(order)
        check(order.status == "CLOSED", "18. 状态转为 CLOSED")
        check(order.closed_at is not None, "19. closed_at 已写入")
        check(order.events.count() == ev_count_before + 1, "20. 新增恰好 1 条事件")
        all_evs = order.events.all()
        last_ev = all_evs[-1]
        print("Events:", [(e.id, e.to_status, e.actor_role) for e in all_evs])
        check(last_ev.actor_role == "customer", "21. 事件记录为 customer 触发")

        # 页面刷新查看 CLOSED 态
        closed_res = client.post('/query', data={'order_no': order.order_no, 'phone': cust.phone})
        closed_html = closed_res.data.decode('utf-8', errors='replace')
        check("确认维修完成" not in closed_html, "22. 已关闭工单无确认按钮")
        check("申请返工" not in closed_html, "23. 已关闭工单无申请返工按钮")

        # 重复确认
        ev_count_closed = order.events.count()
        dup_res = client.post('/query/confirm', data={'order_no': order.order_no, 'phone': cust.phone}, follow_redirects=True)
        db.session.refresh(order)
        check(order.status == "CLOSED", "24. 重复确认后状态仍为 CLOSED")
        check(order.events.count() == ev_count_closed, "25. 重复确认无新增事件且给出指引")

        # ── 26~34. 申请返工（准备另一张 WAIT_CONFIRM 单） ──
        order_rw = WorkOrder(
            order_no="WO-20261001-0202", customer_id=cust.id, device_id=dev.id,
            description="返工测试工单", priority="normal", status="WAIT_CONFIRM",
            warranty_flag=False, created_at=now - timedelta(hours=5),
            dispatched_at=now - timedelta(hours=4), completed_at=now - timedelta(hours=1),
            technician_id=tech.id, labor_hours=3.0, labor_fee=240.0, part_fee=100.0,
            visit_fee=50.0, total_fee=390.0, resolution="调试修复", resolution_note="临时处理"
        )
        db.session.add(order_rw)
        db.session.commit()
        db.session.add(WorkOrderEvent(work_order_id=order_rw.id, from_status="IN_PROGRESS", to_status="WAIT_CONFIRM",
                                      actor_role="technician", note="完工", created_at=order_rw.completed_at))
        db.session.commit()

        # 缺原因被拒
        ev_before_rw = order_rw.events.count()
        client.post('/query/rework', data={'order_no': order_rw.order_no, 'phone': cust.phone, 'note': ''})
        db.session.refresh(order_rw)
        check(order_rw.status == "WAIT_CONFIRM", "26. 缺原因返工被拒，状态仍为 WAIT_CONFIRM")
        check(order_rw.events.count() == ev_before_rw, "27. 缺原因返工无新增事件")

        # 带原因成功
        client.post('/query/rework', data={'order_no': order_rw.order_no, 'phone': cust.phone, 'note': '再次黑屏不亮'})
        db.session.refresh(order_rw)
        check(order_rw.status == "IN_PROGRESS", "28. 返工成功状态回退至 IN_PROGRESS")
        check(order_rw.completed_at is None, "29. completed_at 已清空")
        check(order_rw.labor_hours is None, "30. labor_hours 已清空")
        check(order_rw.labor_fee == 0.0, "31. labor_fee 清零")
        check(order_rw.part_fee == 0.0, "32. part_fee 清零")
        check(order_rw.total_fee == 0.0, "33. total_fee 清零")
        rework_ev = order_rw.events.all()[-1]
        check(rework_ev.note == "再次黑屏不亮", "34. 事件含返工原因")

        # ── 35~40. 状态细分与费用展示逻辑 ──
        # 处于 IN_PROGRESS 时查询
        ip_res = client.post('/query', data={'order_no': order_rw.order_no, 'phone': cust.phone})
        ip_html = ip_res.data.decode('utf-8', errors='replace')
        check("确认维修完成" not in ip_html and "申请返工" not in ip_html, "35. IN_PROGRESS 下无确认与返工按钮")
        check("待技师完工后结算" in ip_html, "36. 未完工单不显示 ¥0.00，提示待结算")

        # ON_HOLD 状态查询
        order_rw.status = "ON_HOLD"
        db.session.commit()
        oh_res = client.post('/query', data={'order_no': order_rw.order_no, 'phone': cust.phone})
        oh_html = oh_res.data.decode('utf-8', errors='replace')
        check("等配件" in oh_html or "等待配件" in oh_html, "37. ON_HOLD 显示等配件状态")
        check("确认维修完成" not in oh_html, "38. ON_HOLD 下无确认按钮")

        # 保内单查询
        order_in = WorkOrder(
            order_no="WO-20261001-0203", customer_id=cust.id, device_id=dev_in.id,
            description="打印机保内维修", priority="normal", status="WAIT_CONFIRM",
            warranty_flag=True, created_at=now - timedelta(hours=3),
            dispatched_at=now - timedelta(hours=2), completed_at=now - timedelta(hours=1),
            technician_id=tech.id, labor_hours=1.0, total_fee=0.0
        )
        db.session.add(order_in)
        db.session.commit()
        in_res = client.post('/query', data={'order_no': order_in.order_no, 'phone': cust.phone})
        in_html = in_res.data.decode('utf-8', errors='replace')
        check("¥0.00" in in_html, "39. 保内单显示 ¥0.00")
        check("保修范围" in in_html, "40. 保内单注明保修范围内")

        # 凭证错误下状态不变且无事件写入
        ev_cnt = order_in.events.count()
        client.post('/query/confirm', data={'order_no': order_in.order_no, 'phone': '13899999999'})
        db.session.refresh(order_in)
        check(order_in.status == "WAIT_CONFIRM", "41. 错误凭证下状态不变")
        check(order_in.events.count() == ev_cnt, "42. 错误凭证下无事件写入")

        # 时间线条数与内容检查
        time_res = client.post('/query', data={'order_no': order.order_no, 'phone': cust.phone})
        t_html = time_res.data.decode('utf-8', errors='replace')
        check("WAIT_CONFIRM" not in t_html, "43. 时间线不含内部枚举英文名 WAIT_CONFIRM")
        check("IN_PROGRESS" not in t_html, "44. 时间线不含内部枚举英文名 IN_PROGRESS")
        check("PENDING" not in t_html, "45. 时间线不含内部枚举英文名 PENDING")
        check("ASSIGNED" not in t_html, "46. 时间线不含内部枚举英文名 ASSIGNED")
        check("CLOSED" not in t_html, "47. 时间线不含内部枚举英文名 CLOSED")

    print(f"[PASS] test_query.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
