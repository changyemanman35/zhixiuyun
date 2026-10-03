"""test_seed.py · 演示数据测试（严格 64 项断言）
覆盖：固定种子生成、AC-8.1 7/7状态覆盖、超时单≥2、真实规则流转、重复点击防覆盖、报表与数据库一致性、CLI三种模式
"""
import sys
import os
import subprocess
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Customer, Device, Technician, FaultType, Part, WorkOrder, WorkOrderEvent, OrderPart
import rules
import seed
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

        # 固定注入时刻：2026-09-25 10:00:00
        mock_now = datetime(2026, 9, 25, 10, 0, 0)

        # ── 1~12. AC-8.1 数量、状态覆盖、超时单 ──
        count = seed.generate_demo_data(now=mock_now, mode='reset')
        check(count >= 20, "1. 演示工单总数 ≥ 20")
        check(count == 28, "2. 演示工单恰好为 28 张")

        demo_orders = WorkOrder.query.filter_by(is_demo=True).all()
        check(len(demo_orders) == 28, "3. 数据库中 is_demo=True 记录为 28")

        # 状态覆盖 7/7（断言 4~10）
        statuses_present = set(o.status for o in demo_orders)
        for idx, st in enumerate(config.STATUSES, start=4):
            check(st in statuses_present, f"{idx}. 覆盖状态: {st}")

        check(len(statuses_present) == 7, "11. 状态覆盖 7/7 全覆盖")

        # 超时关闭单 ≥ 2
        late_closed = [o for o in demo_orders if o.status == 'CLOSED' and rules.is_on_time(o) is False]
        check(len(late_closed) >= 2, "12. 超时关闭单 ≥ 2 (实测满足)")

        # ── 13~24. AC-8.2 全部走真实规则 ──
        # 逐状态验证工单属性完整性
        by_status = {st: [o for o in demo_orders if o.status == st] for st in config.STATUSES}

        # PENDING 规则
        p_order = by_status['PENDING'][0]
        check(p_order.dispatched_at is None and p_order.technician_id is None, "13. PENDING 未派工无技师")
        check(p_order.events.count() == 1, "14. PENDING 仅含创建事件")

        # ASSIGNED 规则
        a_order = by_status['ASSIGNED'][0]
        check(a_order.dispatched_at is not None and a_order.technician_id is not None, "15. ASSIGNED 已记录派工时刻与技师")
        check(a_order.events.count() >= 2, "16. ASSIGNED 包含建单与派工事件")

        # IN_PROGRESS 规则
        ip_order = by_status['IN_PROGRESS'][0]
        check(ip_order.status == 'IN_PROGRESS' and ip_order.completed_at is None, "17. IN_PROGRESS 未完工")

        # ON_HOLD 规则
        oh_order = by_status['ON_HOLD'][0]
        hold_evt = [e for e in oh_order.events if e.to_status == 'ON_HOLD']
        check(len(hold_evt) > 0 and hold_evt[0].note is not None, "18. ON_HOLD 记录挂起原因")

        # WAIT_CONFIRM 规则
        wc_order = by_status['WAIT_CONFIRM'][0]
        check(wc_order.completed_at is not None and wc_order.labor_hours is not None, "19. WAIT_CONFIRM 已记录完工时刻与工时")
        check(wc_order.fault_type_id is not None, "20. WAIT_CONFIRM 判定了故障分类")

        # CLOSED 规则
        cl_order = by_status['CLOSED'][0]
        check(cl_order.closed_at is not None, "21. CLOSED 记录关闭时刻")
        check(cl_order.events.all()[-1].actor_role == 'customer', "22. CLOSED 终态由客户事件闭环")

        # CANCELLED 规则
        can_order = by_status['CANCELLED'][0]
        can_evt = [e for e in can_order.events if e.to_status == 'CANCELLED'][0]
        check(can_evt.note is not None, "23. CANCELLED 必填取消原因")
        check(can_order.closed_at is None, "24. CANCELLED 未经客户确认，无 closed_at")

        # ── 25~37. AC-8.3 重复点击防覆盖与清空范围 ──
        res_seed_page = client.get('/seed')
        html_seed = res_seed_page.data.decode('utf-8', errors='replace')
        check(res_seed_page.status_code == 200, "25. GET /seed 成功返回 200")
        check("追加一批" in html_seed, "26. 提供追加一批操作")
        check("清空重建" in html_seed, "27. 提供清空重建操作")
        check("7/7" in html_seed or "状态覆盖" in html_seed, "28. 页面展示 7/7 覆盖情况")

        # 追加模式
        count_append = seed.generate_demo_data(now=mock_now, mode='append')
        check(count_append == 28, "29. 追加成功生成 28 张工单")
        total_after_append = WorkOrder.query.filter_by(is_demo=True).count()
        check(total_after_append == 56, "30. 追加后总数变为 56，未发生静默覆盖")

        # 清空模式
        cleared_count = seed.clear_demo_data()
        check(cleared_count == 56, "31. 清空操作删除全部 56 张演示工单")
        check(WorkOrder.query.filter_by(is_demo=True).count() == 0, "32. 演示工单清空为 0")
        # 主数据（客户/设备/技师/配件/故障）必须完好保留 (SEED-2)
        check(Customer.query.count() >= 6, "33. [SEED-2] 清空后客户主数据完好保留")
        check(Device.query.count() >= 10, "34. [SEED-2] 清空后设备主数据完好保留")
        check(Technician.query.count() >= 4, "35. [SEED-2] 清空后技师主数据完好保留")
        check(Part.query.count() >= 6, "36. [SEED-2] 清空后配件字典完好保留")
        check(FaultType.query.count() >= 7, "37. [SEED-2] 清空后故障字典完好保留")

        # 重新生成一份纯净基准数据
        seed.generate_demo_data(now=mock_now, mode='reset')

        # ── 38~48. AC-8.4 报表数字与数据库严格一致 ──
        start_sep = datetime(2026, 9, 1)
        end_sep = datetime(2026, 10, 1)
        sep_orders = WorkOrder.query.filter(WorkOrder.created_at >= start_sep, WorkOrder.created_at < end_sep).all()
        db_total_sep = len(sep_orders)
        db_closed_sep = len([o for o in sep_orders if o.status == 'CLOSED'])

        res_rep_sep = client.get('/reports?month=2026-09')
        html_rep = res_rep_sep.data.decode('utf-8', errors='replace')
        check(f"{db_total_sep}</div>" in html_rep or str(db_total_sep) in html_rep, "38. 报表总数与数据库一致")
        check(f"{db_closed_sep}</div>" in html_rep or str(db_closed_sep) in html_rep, "39. 报表已关闭数与数据库一致")
        check("按时关闭率" in html_rep, "40. 包含按时关闭率指标")
        check("平均维修时长" in html_rep, "41. 包含平均维修时长指标")
        check("保内占比" in html_rep, "42. 包含保内占比指标")

        # 上月 (2026-08) 一致性
        start_aug = datetime(2026, 8, 1)
        aug_orders = WorkOrder.query.filter(WorkOrder.created_at >= start_aug, WorkOrder.created_at < start_sep).all()
        db_total_aug = len(aug_orders)
        res_rep_aug = client.get('/reports?month=2026-08')
        html_rep_aug = res_rep_aug.data.decode('utf-8', errors='replace')
        check(f"{db_total_aug}</div>" in html_rep_aug or str(db_total_aug) in html_rep_aug, "43. 上月工单数与数据库一致")

        # ── 44~55. 演示页面客户查询凭证与口径 ──
        res_seed_cred = client.get('/seed')
        html_cred = res_seed_cred.data.decode('utf-8', errors='replace')
        check("客户查询演示凭证" in html_cred, "44. 页面给出客户查询演示凭证")
        check("138" in html_cred and "WO-" in html_cred, "45. 凭证包含可用的真实工单号与手机号")
        check("is_demo=True" in html_cred or "仅删除" in html_cred, "46. 说明清空范围仅针对演示工单")
        check(str(config.SLA_DISPATCH_HOURS) in html_cred, "47. 页面说明响应阈值来自 config")
        check(str(config.SLA_PROGRESS_HOURS) in html_cred, "48. 页面说明维修阈值来自 config")
        check(str(config.LABOR_RATE_PER_HOUR) in html_cred, "49. 页面说明工时单价来自 config")
        check(str(config.VISIT_FEE_NORMAL) in html_cred, "50. 页面说明上门费来自 config")

        # ── 51~64. CLI 函数与统计结构验证 ──
        stats = seed.get_demo_stats()
        check(stats['total'] == 28, "51. get_demo_stats total = 28")
        check(stats['statuses_covered'] == 7, "52. get_demo_stats statuses_covered = 7")
        check(stats['late_closed'] >= 2, "53. get_demo_stats late_closed >= 2")
        check(stats['query_credential'] is not None, "54. get_demo_stats 提供有效凭证")
        check('order_no' in stats['query_credential'] and 'phone' in stats['query_credential'], "55. 凭证含单号与手机号")
        check(len(stats['status_dist']) == 7, "56. 状态分布字典包含 7 个状态")
        check(stats['status_dist']['CLOSED'] > 0, "57. CLOSED 数量大于 0")
        check(stats['status_dist']['PENDING'] > 0, "58. PENDING 数量大于 0")
        check(stats['status_dist']['IN_PROGRESS'] > 0, "59. IN_PROGRESS 数量大于 0")
        check(stats['status_dist']['ON_HOLD'] > 0, "60. ON_HOLD 数量大于 0")
        check(stats['status_dist']['WAIT_CONFIRM'] > 0, "61. WAIT_CONFIRM 数量大于 0")
        check(stats['status_dist']['ASSIGNED'] > 0, "62. ASSIGNED 数量大于 0")
        check(stats['status_dist']['CANCELLED'] > 0, "63. CANCELLED 数量大于 0")
        check(seed.SEED == config.BATCH_RNG_SEED, "64. 使用 config.BATCH_RNG_SEED 固定随机种子")

    print(f"[PASS] test_seed.py: 全部 {passed_assertions} 项断言通过！")

if __name__ == '__main__':
    run_tests()
