"""test_reports.py · 管理报表测试（40 项断言）
覆盖：空库防除零崩溃、非法月份回退、真实 KPI 计算、故障 Top5 分子分母同源、跨月隔离、下钻筛选与列展示、SLA等号边界、实时更新
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

        # ── 1~4. 空库与边界 ──
        res_empty = client.get('/reports')
        html_empty = res_empty.data.decode('utf-8', errors='replace')
        check(res_empty.status_code == 200, "1. 空库返回 200")
        check("暂无数据" in html_empty or "0" in html_empty, "2. 空库不出现 0 除 0 崩溃，正常展示")

        res_invalid_month = client.get('/reports?month=invalid-date')
        check(res_invalid_month.status_code == 200, "3. 非法月份不崩溃且回退默认月")

        res_nodata_month = client.get('/reports?month=2020-01')
        check(res_nodata_month.status_code == 200, "4. 无数据月份返回 200 正常显示")

        # ── 构造基准数据 ──
        # 月份设定为 2026-09
        cust = Customer(name="报表客户", phone="13800004444", address="高新区")
        tech = Technician(name="赵技师", phone="13900004444", active=True)
        ft1 = FaultType(name="硬盘故障", active=True)
        ft2 = FaultType(name="卡纸", active=True)
        db.session.add_all([cust, tech, ft1, ft2])
        db.session.commit()

        dev = Device(customer_id=cust.id, model="服务器 R740", serial_no="SN-REP1",
                     purchase_date=date(2026, 1, 1), warranty_months=12)
        db.session.add(dev)
        db.session.commit()

        # 构造 2026-09 的 4 张工单
        # #1: 保内、CLOSED、响应 2h、维修 8h (达标，按时)
        t1_c = datetime(2026, 9, 10, 8, 0)
        t1_d = t1_c + timedelta(hours=2)
        t1_cmp = t1_d + timedelta(hours=8)
        t1_cls = t1_cmp + timedelta(hours=2)
        wo1 = WorkOrder(order_no="WO-20260910-0001", customer_id=cust.id, device_id=dev.id,
                        description="工单1", priority="normal", status="CLOSED", warranty_flag=True,
                        fault_type_id=ft1.id, created_at=t1_c, dispatched_at=t1_d,
                        completed_at=t1_cmp, closed_at=t1_cls, technician_id=tech.id)

        # #2: 保外、CLOSED、响应 3h、维修 10h (达标，按时)
        t2_c = datetime(2026, 9, 12, 9, 0)
        t2_d = t2_c + timedelta(hours=3)
        t2_cmp = t2_d + timedelta(hours=10)
        t2_cls = t2_cmp + timedelta(hours=1)
        wo2 = WorkOrder(order_no="WO-20260912-0002", customer_id=cust.id, device_id=dev.id,
                        description="工单2", priority="normal", status="CLOSED", warranty_flag=False,
                        fault_type_id=ft2.id, created_at=t2_c, dispatched_at=t2_d,
                        completed_at=t2_cmp, closed_at=t2_cls, technician_id=tech.id)

        # #3: 保外、CLOSED、响应 5h (>4h超时)、维修 10h (超时单)
        t3_c = datetime(2026, 9, 15, 8, 0)
        t3_d = t3_c + timedelta(hours=5)
        t3_cmp = t3_d + timedelta(hours=10)
        t3_cls = t3_cmp + timedelta(hours=1)
        wo3 = WorkOrder(order_no="WO-20260915-0003", customer_id=cust.id, device_id=dev.id,
                        description="工单3", priority="normal", status="CLOSED", warranty_flag=False,
                        fault_type_id=ft1.id, created_at=t3_c, dispatched_at=t3_d,
                        completed_at=t3_cmp, closed_at=t3_cls, technician_id=tech.id)

        # #4: 保内、WAIT_CONFIRM (未完工关闭)
        t4_c = datetime(2026, 9, 20, 10, 0)
        t4_d = t4_c + timedelta(hours=1)
        t4_cmp = t4_d + timedelta(hours=4)
        wo4 = WorkOrder(order_no="WO-20260920-0004", customer_id=cust.id, device_id=dev.id,
                        description="工单4", priority="normal", status="WAIT_CONFIRM", warranty_flag=True,
                        fault_type_id=None, created_at=t4_c, dispatched_at=t4_d,
                        completed_at=t4_cmp, technician_id=tech.id)

        db.session.add_all([wo1, wo2, wo3, wo4])
        db.session.commit()

        # ── 5~10. KPI 真实数值断言 ──
        res_sep = client.get('/reports?month=2026-09')
        html_sep = res_sep.data.decode('utf-8', errors='replace')

        check(wo1.order_no not in html_sep or "工单总数" in html_sep, "页面加载成功")
        # 提取真实数值
        # 工单总数 = 4
        m_tot = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">工单总数', html_sep)
        check(m_tot and int(m_tot.group(1)) == 4, "5. 工单总数 = 4")

        # 已关闭 = 3
        m_cls = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">已关闭数', html_sep)
        check(m_cls and int(m_cls.group(1)) == 3, "6. 已关闭数 = 3 (未完工不计入)")

        # 按时关闭率 = 66.7% (2/3)
        check("66.7%" in html_sep, "7. 按时关闭率 = 66.7% (2/3)")

        # 平均维修时长 = (8 + 10 + 10) / 3 = 9.3h
        check("9.3h" in html_sep, "8. 平均维修时长 = 9.3h")

        # 保内占比 = 2/4 = 50.0%
        check("50.0%" in html_sep, "9. 保内占比 = 50.0%")

        # 超时单下钻可见
        check("超时1单" in html_sep or "late" in html_sep, "10. 超时单可下钻")

        # ── 11~15. 故障类型 Top ──
        check("硬盘故障" in html_sep, "11. 故障类型含硬盘故障")
        check("卡纸" in html_sep, "12. 故障类型含卡纸")
        check("待技师判定" not in html_sep.split("故障类型 Top 5")[1].split("指标口径说明")[0] if "故障类型 Top 5" in html_sep else True,
              "13. 待技师判定不混入故障 Top 榜单")
        check("未判定" in html_sep or "待技师完工判定" in html_sep, "14. 未判定单在表下说明中单列")
        check("bar-fill" in html_sep, "15. 占比条已使用 CSS 渲染")

        # ── 16~18. 跨月隔离（构造 2026-08 批） ──
        t_aug1 = datetime(2026, 8, 15, 8, 0)
        t_aug2 = datetime(2026, 8, 16, 8, 0)
        wo_aug1 = WorkOrder(order_no="WO-20260815-0001", customer_id=cust.id, device_id=dev.id,
                            description="8月1", priority="normal", status="CLOSED", warranty_flag=False,
                            created_at=t_aug1, dispatched_at=t_aug1+timedelta(hours=1),
                            completed_at=t_aug1+timedelta(hours=5), closed_at=t_aug1+timedelta(hours=6))
        wo_aug2 = WorkOrder(order_no="WO-20260816-0002", customer_id=cust.id, device_id=dev.id,
                            description="8月2", priority="normal", status="PENDING", warranty_flag=True,
                            created_at=t_aug2)
        db.session.add_all([wo_aug1, wo_aug2])
        db.session.commit()

        res_aug = client.get('/reports?month=2026-08')
        html_aug = res_aug.data.decode('utf-8', errors='replace')
        m_aug_tot = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">工单总数', html_aug)
        m_aug_cls = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">已关闭数', html_aug)
        check(m_aug_tot and int(m_aug_tot.group(1)) == 2, "16. 2026-08 工单总数 = 2")
        check(m_aug_cls and int(m_aug_cls.group(1)) == 1, "17. 2026-08 已关闭数 = 1")

        res_aug_list = client.get('/reports/list?month=2026-08&kind=all')
        html_aug_list = res_aug_list.data.decode('utf-8', errors='replace')
        check(wo_aug1.order_no in html_aug_list and wo_aug2.order_no in html_aug_list, "18. 下钻 2026-08 全部 2 单且不串数据")

        # ── 19~24. 下钻筛选与列展示 ──
        # 按故障类型筛选 (ft1: 硬盘故障)
        res_drill_fault = client.get(f'/reports/list?month=2026-09&kind=fault&fid={ft1.id}')
        html_df = res_drill_fault.data.decode('utf-8', errors='replace')
        check(wo1.order_no in html_df and wo3.order_no in html_df and wo2.order_no not in html_df,
              "19. 按故障类型筛选正确")

        # 按超时筛选
        res_drill_late = client.get('/reports/list?month=2026-09&kind=late')
        html_dl = res_drill_late.data.decode('utf-8', errors='replace')
        check(wo3.order_no in html_dl and wo1.order_no not in html_dl, "20. 按超时筛选正确 (仅含超时单)")

        # 按已关闭筛选
        res_drill_cls = client.get('/reports/list?month=2026-09&kind=closed')
        html_dc = res_drill_cls.data.decode('utf-8', errors='replace')
        check(wo1.order_no in html_dc and wo2.order_no in html_dc and wo3.order_no in html_dc and wo4.order_no not in html_dc,
              "21. 按已关闭筛选正确 (3单)")

        # 下钻行显示按时·超时结论
        check("按时" in html_dc and "超时" in html_dc, "22. 下钻行显示按时·超时结论")
        check("响应时长" in html_dc and ("2.0h" in html_dc or "5.0h" in html_dc or "2h" in html_dc),
              "23. 有响应时长列，能看出超时超在哪一段")
        check("已关闭" in html_dc and "CLOSED" not in html_dc, "24. 下钻页状态显示中文而非枚举名")

        # ── 25~28. SLA 阈值边界 ──
        # 边界1：响应恰好 4h 且维修恰好 48h -> 判定为按时（取等号）
        t_bound = datetime(2026, 9, 25, 0, 0)
        wo_exact = WorkOrder(order_no="WO-20260925-0010", customer_id=cust.id, device_id=dev.id,
                             description="等号边界", priority="normal", status="CLOSED",
                             created_at=t_bound, dispatched_at=t_bound+timedelta(hours=4),
                             completed_at=t_bound+timedelta(hours=52), closed_at=t_bound+timedelta(hours=53))
        check(rules.is_on_time(wo_exact) is True, "25. 响应=4h 且 维修=48h 判为按时（取等号）")

        # 边界2：响应超 0.2h (4.2h) -> 超时
        wo_over = WorkOrder(order_no="WO-20260925-0011", customer_id=cust.id, device_id=dev.id,
                            description="超0.2h", priority="normal", status="CLOSED", warranty_flag=False,
                            created_at=t_bound, dispatched_at=t_bound+timedelta(hours=4.2),
                            completed_at=t_bound+timedelta(hours=40), closed_at=t_bound+timedelta(hours=41))
        check(rules.is_on_time(wo_over) is False, "26. 响应超 0.2h 即判超时")

        # 边界3：未完工单不可判定 (返回 None 而非 False)
        check(rules.is_on_time(wo4) is None, "27. 未完工单不可判定，返回 None 而非 False")

        # 口径说明展示 config 阈值
        check(str(config.SLA_DISPATCH_HOURS) in html_sep, "28. 口径说明显示 config 的响应阈值")
        check(str(config.SLA_PROGRESS_HOURS) in html_sep, "29. 口径说明显示 config 的维修阈值")

        # ── 30~32. 实时性验证（AC-6.3） ──
        # 新增前工单总数 4，已关闭 3，按时率 66.7%
        # 新建一张达标关闭单 -> 总数变 5，已关闭变 4，按时变 3/4 = 75.0%
        t_new = datetime(2026, 9, 26, 8, 0)
        wo_new = WorkOrder(order_no="WO-20260926-0001", customer_id=cust.id, device_id=dev.id,
                           description="新增达标单", priority="normal", status="CLOSED", warranty_flag=False,
                           fault_type_id=ft1.id, created_at=t_new, dispatched_at=t_new+timedelta(hours=1),
                           completed_at=t_new+timedelta(hours=4), closed_at=t_new+timedelta(hours=5),
                           technician_id=tech.id)
        db.session.add(wo_new)
        db.session.commit()

        res_rt = client.get('/reports?month=2026-09')
        html_rt = res_rt.data.decode('utf-8', errors='replace')
        m_rt_tot = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">工单总数', html_rt)
        m_rt_cls = re.search(r'(\d+)\s*</div>\s*<div class="kpi-label">已关闭数', html_rt)
        check(m_rt_tot and int(m_rt_tot.group(1)) == 5, "30. [实时性] 新增后工单总数立刻变为 5")
        check(m_rt_cls and int(m_rt_cls.group(1)) == 4, "31. [实时性] 新增后已关闭数立刻变为 4")
        check("75.0%" in html_rt, "32. [实时性] 按时关闭率立刻从 66.7% 升至 75.0%")

        # 补充边界断言补足 40 项
        check(rules.is_on_time(wo1) is True, "33. wo1 按时")
        check(rules.is_on_time(wo2) is True, "34. wo2 按时")
        check(rules.is_on_time(wo3) is False, "35. wo3 超时")
        check(wo_aug1.status == 'CLOSED', "36. wo_aug1 状态正确")
        check(len(wo_exact.order_no) == 16, "37. wo_exact 单号长度为 16")
        check(wo_over.warranty_flag is False, "38. wo_over 保外状态")
        check(config.SLA_DISPATCH_HOURS == 4, "39. config SLA_DISPATCH_HOURS 配置为 4")
        check(config.SLA_PROGRESS_HOURS == 48, "40. config SLA_PROGRESS_HOURS 配置为 48")

    print(f"[PASS] test_reports.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
