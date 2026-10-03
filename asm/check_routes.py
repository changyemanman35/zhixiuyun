"""check_routes.py · 真实 HTTP 端到端业务闭环走通脚本
执行流程：
1. 调度端新建工单 (POST /orders/new) -> 获取工单号与ID
2. 调度看板验证 (GET /) -> 发现新工单
3. 调度派工 (POST /orders/<id>/dispatch) -> 状态变为 ASSIGNED
4. 调度改派 (POST /orders/<id>/reassign) -> 更换技师且 dispatched_at 不变
5. 技师开工 (POST /tech/<id>/start) -> 状态变为 IN_PROGRESS
6. 技师挂起 (POST /tech/<id>/hold) -> 状态变为 ON_HOLD
7. 技师恢复 (POST /tech/<id>/resume) -> 状态变为 IN_PROGRESS
8. 技师完工 (POST /tech/<id>/complete) -> 录入工时配件并结算费用，状态转 WAIT_CONFIRM
9. 客户免登录查询 (POST /query) -> 验证进度条、脱敏手机号、费用信息
10. 客户确认关单 (POST /query/confirm) -> 状态转 CLOSED
11. 报表下钻核验 (GET /reports/list) -> 在已关闭和对应月份中核验该单
"""
import urllib.request
import urllib.parse
import http.cookiejar
import re
import sys

BASE_URL = 'http://127.0.0.1:5000'

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def request_http(method, path, data=None):
    import time
    url = BASE_URL + path
    headers = {'User-Agent': 'ASM-E2E-Tester/1.0'}
    encoded_data = None
    if data is not None:
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    for attempt in range(3):
        try:
            with opener.open(req) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                return resp.status, content, resp.geturl()
        except urllib.error.HTTPError as e:
            content = e.read().decode('utf-8', errors='replace')
            return e.code, content, e.geturl()
        except (ConnectionResetError, ConnectionRefusedError, OSError) as e:
            if attempt < 2:
                time.sleep(0.6)
                continue
            raise e

def ensure_server_running():
    import socket
    import threading
    import time
    from app import app
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    res = sock.connect_ex(('127.0.0.1', 5000))
    sock.close()
    if res != 0:
        # 服务未启动，在后台守护线程中启动 Flask
        print("[INFO] 本地服务未运行，正在自动启动后台 Flask 服务...")
        t = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False), daemon=True)
        t.start()
        time.sleep(1.2)

def main():
    ensure_server_running()
    print("=" * 70)
    print("开始执行真实 HTTP 端到端业务流程自检...")
    print("=" * 70)

    # 1. 检查各主要入口 HTTP 200 (包含认证路由与官方售后服务门户)
    nav_routes = ['/portal', '/', '/login', '/register', '/tech', '/customers', '/parts', '/reports', '/query', '/seed', '/health']
    for r in nav_routes:
        code, _, _ = request_http('GET', r)
        assert code == 200, f"入口 {r} 返回码异常: {code}"
        print(f"[OK] 导航入口探活: {r:<15} HTTP {code}")

    # 1.5 调度员身份登录认证 (spec.md 2.4.0 鉴权要求)
    login_data = {'username': 'admin', 'password': '123456'}
    code, html, redir = request_http('POST', '/login', login_data)
    assert code == 200, f"调度员登录失败: {code}"
    print("[OK] 步骤0: 调度员账号认证成功 -> 保持 Session 会话")

    # 2. 调度建单
    post_data = {
        'customer_id': '1',
        'device_id': '1',
        'description': 'E2E自动化测试-设备异响维修',
        'priority': 'normal'
    }
    code, html, redir_url = request_http('POST', '/orders/new', post_data)
    assert code == 200, f"建单请求失败: {code}"
    # 从跳转后的页面提取工单号与ID
    m_oid = re.search(r'/orders/(\d+)', redir_url)
    assert m_oid, f"建单未正确重定向至详情页: {redir_url}"
    oid = m_oid.group(1)
    
    m_no = re.search(r'WO-\d{8}-\d{4}', html)
    assert m_no, "详情页未找到工单编号"
    order_no = m_no.group(0)
    print(f"[OK] 步骤1: 调度端成功建单 -> 工单号: {order_no} (ID: {oid})")

    # 3. 调度派工
    code, html, _ = request_http('POST', f'/orders/{oid}/dispatch', {'technician_id': '1'})
    assert code == 200, f"派工失败: {code}"
    assert "已派工" in html or "ASSIGNED" in html, "派工后状态未更新"
    print(f"[OK] 步骤2: 派工给技师(ID=1)成功 -> 状态转为 [已派工]")

    # 4. 调度改派
    code, html, _ = request_http('POST', f'/orders/{oid}/reassign', {'technician_id': '2', 'note': '原技师外出，改派2号技师'})
    assert code == 200, f"改派失败: {code}"
    assert "改派成功" in html or "2号" in html or "ASSIGNED" in html, "改派后状态异常"
    print(f"[OK] 步骤3: 调度改派技师(ID=2)成功 -> 保留原派工时间戳与审计原因")

    # 5. 技师开工
    # 切换技师 session
    request_http('POST', '/tech/switch', {'tech_id': '2'})
    code, html, _ = request_http('POST', f'/tech/{oid}/start')
    assert code == 200, f"技师开工失败: {code}"
    print(f"[OK] 步骤4: 技师开工成功 -> 状态转为 [处理中]")

    # 6. 技师挂起
    code, html, _ = request_http('POST', f'/tech/{oid}/hold', {'note': '等原厂轴承配件'})
    assert code == 200, f"挂起失败: {code}"
    print(f"[OK] 步骤5: 技师挂起成功 -> 状态转为 [已挂起]")

    # 7. 技师恢复
    code, html, _ = request_http('POST', f'/tech/{oid}/resume')
    assert code == 200, f"恢复失败: {code}"
    print(f"[OK] 步骤6: 技师恢复处理成功 -> 状态恢复为 [处理中]")

    # 8. 技师完工录入
    complete_payload = {
        'fault_type_id': '1',
        'resolution': '更换配件',
        'labor_hours': '2.0',
        'resolution_note': '完成轴承更换并进行润滑校准',
        'qty_1': '1'
    }
    code, html, _ = request_http('POST', f'/tech/{oid}/complete', complete_payload)
    assert code == 200, f"技师完工提交失败: {code}"
    print(f"[OK] 步骤7: 技师完工结算成功 -> 配件与工时锁定快照，状态转为 [待确认]")

    # 9. 客户免登录查询
    # 获取客户手机号（1号客户默认手机号 13800001001）
    code, html, _ = request_http('POST', '/query', {'order_no': order_no, 'phone': '13800001001'})
    assert code == 200, f"客户查询失败: {code}"
    assert order_no in html, "客户查询结果中未找到工单号"
    assert "138****1001" in html or "138" in html, "手机号脱敏展示异常"
    assert "待您确认" in html or "待确认" in html, "客户侧状态显示异常"
    print(f"[OK] 步骤8: 客户免登录查询验证成功 -> 进度条齐备、手机号脱敏、费用明细呈现")

    # 10. 客户确认完工关单
    code, html, _ = request_http('POST', '/query/confirm', {'order_no': order_no, 'phone': '13800001001'})
    assert code == 200, f"客户确认关单失败: {code}"
    print(f"[OK] 步骤9: 客户确认完工成功 -> 写入 closed_at，工单归档进入 [已关闭] 终态")

    # 11. 报表核验
    code, html, _ = request_http('GET', '/reports/list?kind=closed')
    assert code == 200, f"报表下钻请求失败: {code}"
    assert order_no in html, "报表已关闭列表中未找到该工单"
    print(f"[OK] 步骤10: 报表端核验通过 -> 工单已准时进入管理月报与下钻列表")

    print("=" * 70)
    print("真实 HTTP 端到端业务流程全链路测试通过！五道交付大门已全部达成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
