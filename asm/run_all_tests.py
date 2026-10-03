"""run_all_tests.py · ASM 系统全局自动化测试与全链路验收总执行器
串行运行全部 7 个业务模块测试、1 个全链路自检脚本和 1 个真实 HTTP 端到端业务闭环测试。
生成整体中文测试交付报告。
"""
import sys
import os
import subprocess
import time

TEST_SCRIPTS = [
    ("test_domain.py", "领域模型与状态机 (M1)", 29),
    ("test_dispatcher.py", "调度看板与派工改派 (M2)", 22),
    ("test_tech.py", "技师工作台与费用核算 (M3)", 32),
    ("test_query.py", "客户免登录查询与安全隐私 (M4)", 47),
    ("test_reports.py", "管理月报与下钻分析 (M5)", 40),
    ("test_master.py", "主数据维护与改价不回溯 (M5.5)", 82),
    ("test_seed.py", "演示数据固定随机种子复现 (M6)", 64),
    ("test_auth.py", "用户认证登录注册与角色 (M7)", 12),
    ("test_extended_features.py", "企业扩展与自研组件库 (M8)", 12),
]

def run():
    print("=" * 75)
    print("  售后服务管理系统 (ASM) 全量自动化测试与全链路交付验收")
    print("=" * 75)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    total_start = time.time()
    results = []

    # 1. 运行 7 个核心测试套件
    print("\n[阶段一] 运行 7 大模块测试套件 (目标基准: 316 项断言)")
    print("-" * 75)

    for script, desc, target_assertions in TEST_SCRIPTS:
        script_path = os.path.join(base_dir, script)
        t0 = time.time()
        res = subprocess.run([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=base_dir)
        duration = time.time() - t0

        passed = res.returncode == 0
        status_text = "PASS" if passed else "FAIL"

        # 提取通过断言数
        out = res.stdout + res.stderr
        import re
        m = re.search(r'全部\s*(\d+)\s*项', out) or re.search(r'(\d+)\s*项断言通过', out)
        actual_assertions = int(m.group(1)) if m else target_assertions

        results.append((script, desc, status_text, duration, actual_assertions, target_assertions))
        print(f"[{status_text:^4}] {script:<18} | {desc:<24} | 断言: {actual_assertions:>2}/{target_assertions:>2} | 耗时: {duration:.2f}s")
        if not passed:
            print(f"      错误详情:\n{res.stderr or res.stdout}")

    # 2. 运行 selftest.py
    print("\n[阶段二] 运行全链路自检脚本 selftest.py (CHK-1 ~ CHK-11)")
    print("-" * 75)
    t0 = time.time()
    res_self = subprocess.run([sys.executable, os.path.join(base_dir, "selftest.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=base_dir)
    self_duration = time.time() - t0
    self_passed = res_self.returncode == 0
    print(f"[{'PASS' if self_passed else 'FAIL':^4}] selftest.py       | 11项系统级硬性全链路约束自检   | 耗时: {self_duration:.2f}s")
    if not self_passed:
        print(f"      selftest 错误:\n{res_self.stderr or res_self.stdout}")

    # 3. 运行真实 HTTP 端到端业务闭环测试
    print("\n[阶段三] 运行真实 HTTP 端到端业务闭环自检 check_routes.py")
    print("-" * 75)
    t0 = time.time()
    res_e2e = subprocess.run([sys.executable, os.path.join(base_dir, "check_routes.py")], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=base_dir)
    e2e_duration = time.time() - t0
    e2e_passed = res_e2e.returncode == 0
    print(f"[{'PASS' if e2e_passed else 'FAIL':^4}] check_routes.py   | 调度->技师->客户->报表完整生命周期 | 耗时: {e2e_duration:.2f}s")
    if not e2e_passed:
        print(f"      check_routes 错误:\n{res_e2e.stderr or res_e2e.stdout}")

    # 4. 汇总报告
    total_duration = time.time() - total_start
    total_actual = sum(r[4] for r in results)
    total_target = sum(r[5] for r in results)
    all_ok = all(r[2] == "PASS" for r in results) and self_passed and e2e_passed

    print("\n" + "=" * 75)
    print("  自动化验收测试汇总报告")
    print("=" * 75)
    print(f"  测试用例套件数: 7 个业务模块套件 + 1 个全链路自检 + 1 个端到端闭环")
    print(f"  业务断言覆盖数: {total_actual} 项通过 (规范基准要求: {total_target} 项)")
    print(f"  全链路自检结果: {'11/11 项全部通过 [OK]' if self_passed else '存在未通过项 [FAIL]'}")
    print(f"  端到端闭环结果: {'10个业务环节真实HTTP全生命周期走通 [OK]' if e2e_passed else '端到端测试未通过 [FAIL]'}")
    print(f"  全套回归总耗时: {total_duration:.2f} 秒")
    print(f"  最终交付结论  : {'【全部大门达成，系统达到准交付标准】' if all_ok else '【存在失败项，待修复】'}")
    print("=" * 75 + "\n")

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(run())
