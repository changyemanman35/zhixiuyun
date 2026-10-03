"""test_extended_features.py · 2.3 扩展功能与大厂组件库全套测试套件
测试目标：
1. 预约时段字段读写与有效性
2. 智能派工打分推荐算法 (recommend_technician)
3. 30 天二次返修雷达预警判定 (is_rework_30d)
4. 配件库存充足性校验与超卖拦截守卫
5. 配件库存完工原子扣减
6. 客户完工满意度星级打分 (1~5星) 与服务标签
7. 调度员旧件条码回收核销与审计记录
8. 官方授权服务网点查询接口 (/stations)
9. 标准 A4 官方售后服务报告单渲染 (/orders/<id>/print)
10. 月度财务经营台账 CSV 导出与 UTF-8 BOM 编码 (/reports/export)
11. ASM Copilot 本地离线意图识别、专家问答与敏感信息正则脱敏
12. NFR-6 Zero-CDN 纯离线合规性静态文件扫描
"""
import sys
import os
import unittest
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Customer, Device, Technician, FaultType, Part, WorkOrder, OrderPart, ServiceStation, AIChatLog, utcnow
import rules
import copilot_engine


class TestExtendedFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # ── 1. 预约时段 ──
    def test_appointment_fields(self):
        order = WorkOrder.query.first()
        self.assertIsNotNone(order, "应当存在工单数据")
        order.appointment_date = date(2026, 10, 5)
        order.appointment_slot = '09:00-11:00'
        db.session.commit()

        refreshed = WorkOrder.query.get(order.id)
        self.assertEqual(refreshed.appointment_date, date(2026, 10, 5))
        self.assertEqual(refreshed.appointment_slot, '09:00-11:00')

    # ── 2. 智能派工打分推荐算法 ──
    def test_intelligent_dispatch_recommendation(self):
        order = WorkOrder.query.first()
        active_techs = Technician.query.filter_by(active=True).all()
        self.assertTrue(len(active_techs) > 0, "应有活跃技师")

        recs = rules.recommend_technician(order, active_techs, db.session)
        self.assertEqual(len(recs), len(active_techs))
        self.assertTrue(recs[0]['score'] >= recs[-1]['score'], "推荐列表应当按综合得分降序排列")
        self.assertIn('reason', recs[0], "推荐结果必须包含解释说明原因")

    # ── 3. 30 天二次返修雷达预警判定 ──
    def test_rework_30d_radar(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        now = utcnow()
        dev = Device.query.first()
        self.assertIsNotNone(dev)

        # 构造工单 1
        wo1 = WorkOrder(
            order_no=f"WO-RW1-{uid}",
            customer_id=dev.customer_id,
            device_id=dev.id,
            description="首次故障测试",
            priority="normal",
            status="CLOSED",
            created_at=now - timedelta(days=10)
        )
        db.session.add(wo1)
        db.session.commit()

        # 构造工单 2（10天后发生二次返修）
        wo2 = WorkOrder(
            order_no=f"WO-RW2-{uid}",
            customer_id=dev.customer_id,
            device_id=dev.id,
            description="二次返修测试",
            priority="normal",
            status="PENDING",
            created_at=now
        )
        db.session.add(wo2)
        db.session.commit()

        is_rework = rules.is_rework_30d(wo2, db.session)
        # 清理
        db.session.delete(wo2)
        db.session.delete(wo1)
        db.session.commit()

        self.assertTrue(is_rework, "10天内相同设备的工单必须判定为二次返修")

    # ── 4. 配件库存超卖拦截与原子扣减 ──
    def test_parts_inventory_guard(self):
        import uuid
        # 找出或创建测试备件
        part = Part.query.first()
        self.assertIsNotNone(part)
        initial_stock = part.stock_quantity

        # 登录技师
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'technician'
            sess['current_tech_id'] = 1

        # 为测试创建独立的处于 IN_PROGRESS 状态的工单
        cust = Customer.query.first()
        dev = Device.query.first()
        test_wo = WorkOrder(
            order_no=f"WO-TEST-STOCK-{uuid.uuid4().hex[:6]}",
            customer_id=cust.id,
            device_id=dev.id,
            description="库存测试专用工单",
            status="IN_PROGRESS",
            technician_id=1,
            priority="normal"
        )
        db.session.add(test_wo)
        db.session.commit()

        try:
            # 1. 超卖请求：请求数量大于现有库存
            over_qty = initial_stock + 999
            res_over = self.client.post(f'/tech/{test_wo.id}/complete', data={
                'fault_type_id': 1,
                'resolution': '更换配件',
                'labor_hours': '1.0',
                f'qty_{part.id}': str(over_qty)
            }, follow_redirects=True)
            self.assertIn('库存不足', res_over.data.decode('utf-8'), "库存不足时必须触发超卖拦截守卫")

            # 验证库存未被扣减
            part_refreshed = db.session.get(Part, part.id)
            self.assertEqual(part_refreshed.stock_quantity, initial_stock, "超卖拦截后库存必须保持不变")

            # 2. 正常完工核扣
            deduct_qty = 2
            res_ok = self.client.post(f'/tech/{test_wo.id}/complete', data={
                'fault_type_id': 1,
                'resolution': '更换配件',
                'labor_hours': '1.0',
                f'qty_{part.id}': str(deduct_qty),
                f'old_sn_{part.id}': 'OLD-SN-TEST-8888'
            }, follow_redirects=True)
            self.assertIn('已完工提交', res_ok.data.decode('utf-8'))
            part_after = db.session.get(Part, part.id)
            self.assertEqual(part_after.stock_quantity, initial_stock - deduct_qty, "完工提交后库存必须原子核减")
        finally:
            # 还原测试所扣减的库存
            part.stock_quantity = initial_stock
            # 清理测试工单及其明细
            db.session.delete(test_wo)
            db.session.commit()

    # ── 5. 客户满意度打分与旧件核销 ──
    def test_customer_rating_and_old_parts_verification(self):
        order = WorkOrder.query.filter_by(status='CLOSED').first()
        self.assertIsNotNone(order)

        # 客户评价
        res_rate = self.client.post('/query/rate', data={
            'order_no': order.order_no,
            'phone': order.customer.phone,
            'rating': '5',
            'rating_tags': '准时到达,技术专业',
            'rating_comment': '工程师服务非常细致，完全修好了！'
        }, follow_redirects=True)
        self.assertEqual(res_rate.status_code, 200)

        db.session.expire_all()
        order_refreshed = db.session.get(WorkOrder, order.id)
        self.assertEqual(order_refreshed.rating, 5)
        self.assertEqual(order_refreshed.rating_tags, '准时到达,技术专业')
        self.assertIsNotNone(order_refreshed.rated_at)

        # 调度员核销旧件
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'dispatcher'

        res_verify = self.client.post(f'/orders/{order.id}/verify-old-parts', follow_redirects=True)
        self.assertEqual(res_verify.status_code, 200)
        db.session.expire_all()
        self.assertTrue(db.session.get(WorkOrder, order.id).old_parts_verified, "旧件核销后标志位应置为 True")

    # ── 6. 服务网点查询 ──
    def test_service_stations(self):
        res = self.client.get('/stations')
        self.assertEqual(res.status_code, 200)
        self.assertIn('海尔官方华南旗舰', res.data.decode('utf-8'))

        # 按城市检索
        res_sz = self.client.get('/stations?city=深圳')
        self.assertEqual(res_sz.status_code, 200)
        self.assertIn('深圳市', res_sz.data.decode('utf-8'))

    # ── 7. A4 标准服务单打印视图 ──
    def test_a4_print_order_view(self):
        order = WorkOrder.query.first()
        res = self.client.get(f'/orders/{order.id}/print')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('官方售后维修服务报告单', html)
        self.assertIn(order.order_no, html)
        self.assertIn('质保专用章', html)

    # ── 8. 月度财务经营台账 CSV 导出 ──
    def test_monthly_report_csv_export(self):
        res = self.client.get('/reports/export')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'text/csv')
        content = res.data.decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'), "必须携带 UTF-8 BOM 确保 Windows Excel 打开零乱码")
        self.assertIn('工单编号,客户姓名,客户电话', content)

    # ── 9. ASM Copilot 离线意图识别与敏感脱敏 ──
    def test_copilot_engine_and_api(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        # 脱敏测试
        text_with_phone = "我的手机是 13812345678，住在101室"
        sanitized = copilot_engine.sanitize_text(text_with_phone)
        self.assertNotIn("13812345678", sanitized)
        self.assertIn("138****5678", sanitized)

        # 离线意图测试
        res_diag = copilot_engine.process_copilot_chat("空调开机吹热风，完全不制冷", "customer", "/portal", None, db.session)
        self.assertEqual(res_diag['intent'], 'diagnose')
        self.assertIn('故障预诊断', res_diag['reply'])

        res_insp = copilot_engine.process_copilot_chat("帮我看看今天有哪些超时单和库存告急？", "dispatcher", "/", None, db.session)
        self.assertEqual(res_insp['intent'], 'inspect')

        # API 接口测试
        res_api = self.client.post('/api/copilot/chat', json={
            'message': '你好，你是谁？',
            'context_page': '/portal'
        })
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('Copilot', data['reply'])

    # ── 10. Cloud Enterprise UI 视觉体系与组件完整性检查 ──
    def test_cloud_enterprise_ui_compliance(self):
        res = self.client.get('/portal')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # 验证阿里云极光背景与渐变高光标题
        self.assertIn('cloud-aurora-hero', html, "首页巨幕必须采用阿里云极光柔光流线背景")
        self.assertIn('gradient-text-cloud', html, "必须包含渐变高光核心标题")

        # 验证 Google Cloud 沉浸暗夜卡片阵列
        self.assertIn('gcloud-dark-card', html, "必须包含 Google Cloud 风格沉浸暗夜质感卡片")
        self.assertIn('AI COPILOT POWERED', html)

        # 验证阿里云通义千问六宫格能力矩阵
        self.assertIn('qwen-matrix-container', html, "必须包含通义千问风格售后能力矩阵")
        self.assertIn('qwen-card', html)

        # 验证右下角阿里云悬浮双球体系
        self.assertIn('cloud-floating-dock', html, "全局布局必须包含阿里云悬浮智能双球体系")
        self.assertIn('ball-ai-purple', html)
        self.assertIn('ball-repair-blue', html)

    # ── 11. 在线报修前置鉴权拦截与登录回跳测试 ──
    def test_unauthenticated_order_new_redirect(self):
        # 确保无 session 登录状态
        with self.client.session_transaction() as sess:
            sess.clear()

        # 访客直接请求在线报修表单
        res = self.client.get('/orders/new', headers={'X-Force-Auth': 'true'}, follow_redirects=False)
        self.assertEqual(res.status_code, 302, "未登录访问报修页必须返回 302 重定向")
        self.assertIn('/login', res.location, "重定向目标必须是登录页")
        self.assertTrue('next=/orders/new' in res.location or 'next=%2Forders%2Fnew' in res.location,
                        "重定向必须携带安全回跳参数 next=/orders/new")

    # ── 12. 客户视角设备隔离与报修防越权测试 ──
    def test_customer_device_isolation_and_submission(self):
        # 获取任意客户与其关联设备
        cust = Customer.query.filter(Customer.devices.any()).first()
        self.assertIsNotNone(cust, "应有具备设备的客户")
        cust_devices = cust.devices.all()
        cust_device_ids = [d.id for d in cust_devices]

        # 找一个属于其他客户的设备
        other_device = Device.query.filter(Device.customer_id != cust.id).first()

        # 模拟普通客户身份登录
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9999
            sess['username'] = cust.name
            sess['role'] = 'customer'
            sess['customer_id'] = cust.id

        # 1. 访问 /orders/new 验证设备隔离
        res = self.client.get('/orders/new')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertTrue('报修申请人：' in html or '已认证客户' in html, "客户登录应显示个人身份卡片")
        # 客户自购设备应当在卡片列表中
        self.assertIn(cust_devices[0].model, html)
        if other_device:
            # 确认不包含其他客户专属的罕见序列号/型号卡片标识
            self.assertNotIn(f"data-device-id=\"{other_device.id}\"", html)

        # 2. 客户自助报修提单
        target_device = cust_devices[0]
        res_post = self.client.post('/orders/new', data={
            'device_id': target_device.id,
            'description': '客户自主在线报修测试-空调制冷异常',
            'priority': 'urgent',
            'appointment_date': date.today().strftime('%Y-%m-%d'),
            'appointment_slot': '14:00-16:00'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)

        # 3. 验证数据库中工单正确关联到该客户本人（防越权）
        wo = WorkOrder.query.filter_by(description='客户自主在线报修测试-空调制冷异常').first()
        self.assertIsNotNone(wo, "工单应当成功生成")
        self.assertEqual(wo.customer_id, cust.id, "工单的 customer_id 必须强制绑定当前登录客户本人")
        self.assertEqual(wo.device_id, target_device.id)
        self.assertEqual(wo.appointment_slot, '14:00-16:00')

        # 清理该测试工单
        db.session.delete(wo)
        db.session.commit()

    # ── 16. C2C 动态师傅推荐与 LBS 匹配测试 ──
    def test_dynamic_technician_matching(self):
        # 1. 不带品类
        res = self.client.get('/api/technicians/match')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['code'], 0)
        self.assertGreater(data['count'], 0)
        self.assertIn('distance_km', data['technicians'][0])
        self.assertIn('skill_tags', data['technicians'][0])

        # 2. 带品类匹配（空调）
        res_ac = self.client.get('/api/technicians/match?category=空调')
        self.assertEqual(res_ac.status_code, 200)
        data_ac = res_ac.get_json()
        self.assertEqual(data_ac['code'], 0)
        self.assertTrue(any(t['is_hit'] for t in data_ac['technicians']))

    # ── 17. 安全合规与隐私保护页面测试 ──
    def test_safety_compliance_view(self):
        res = self.client.get('/safety')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('安全合规与隐私保护', html)
        self.assertIn('双向隐私防护', html)
        self.assertIn('资金双向托管', html)

    # ── 18. 师傅招募全景落地页测试 ──
    def test_technician_recruitment_view(self):
        res = self.client.get('/recruit')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('师傅加盟入驻计划', html)
        self.assertIn('传统维修平台 vs 家修无忧平台', html)
    # ── 19. AI 智能助手向导界面测试 (Power AI 原版) ──
    def test_ai_assistant_step_by_step_wizard_view(self):
        res = self.client.get('/ai-assistant')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Power', html)
        self.assertIn('hero-headline-ai', html)
        self.assertIn('Schedule a Consult', html)
        self.assertIn('1. 您需要维修什么家电？', html)
        self.assertIn('下一步：挑选附近师傅 (跳转新界面)', html)

    # ── 20. 第 5 步独立选师傅与雷达大厅新界面测试 ──
    def test_pick_technician_step5_standalone_view_and_order(self):
        # 1. 模拟 Step 1~4 提交进入 Step 5 独立界面
        res_step5 = self.client.post('/orders/pick-technician', data={
            'category': '洗衣机',
            'new_device_model': '海尔变频静音滚筒洗衣机',
            'fault_tags': '脱水不转/震动剧烈',
            'description': '脱水时伴随剧烈撞击异响',
            'appointment_date': '2026-10-06',
            'appointment_slot': '下午 (14:00 - 18:00)',
            'contact_name': '张师傅客户',
            'contact_phone': '13911112222',
            'service_address': '北京市海淀区中关村南大街1号院'
        })
        self.assertEqual(res_step5.status_code, 200)
        html_step5 = res_step5.data.decode('utf-8')
        self.assertIn('第 5 步：在线师傅撮合大厅', html_step5)
        self.assertIn('全城金牌师傅极速广播抢单', html_step5)
        self.assertIn('智修云调度雷达正在为您撮合附近师傅', html_step5)
        self.assertIn('海尔变频静音滚筒洗衣机', html_step5)
        self.assertIn('¥30.00', html_step5)

        # 2. 模拟在第 5 步确认派单 (选择全城广播抢单)
        with self.client.session_transaction() as sess:
            sess['role'] = 'customer'
        res_order = self.client.post('/orders/new', data={
            'new_device_model': '海尔变频静音滚筒洗衣机',
            'description': '[脱水不转/震动剧烈] 脱水时伴随剧烈撞击异响',
            'appointment_date': '2026-10-06',
            'appointment_slot': '下午 (14:00 - 18:00)',
            'contact_name': '张师傅客户',
            'contact_phone': '13911112222',
            'service_address': '北京市海淀区中关村南大街1号院',
            'selected_tech_id': 'broadcast'
        }, follow_redirects=True)
        self.assertEqual(res_order.status_code, 200)

        # 3. 验证数据库中工单与核销码
        wo = WorkOrder.query.filter(WorkOrder.description.like('%脱水不转%')).first()
        self.assertIsNotNone(wo)
        self.assertIsNotNone(wo.checkin_code)
        self.assertEqual(len(wo.checkin_code), 6)
        self.assertEqual(wo.visit_fee, 30.0)

        # 验证关联的客户地址已保存
        cust = Customer.query.get(wo.customer_id)
        self.assertIsNotNone(cust)
        self.assertEqual(cust.phone, '13911112222')

        # 清理该测试工单
        db.session.delete(wo)
        db.session.commit()

    def test_broadcast_order_and_tech_grab_concurrency(self):
        """测试全城抢单大厅撮合、并发防重抢单与双通道视觉断言"""
        # 1. 验证 AI 智能报修页面的双通道按钮与冻结资产守卫
        res_ai = self.client.get('/ai-assistant')
        self.assertEqual(res_ai.status_code, 200)
        html_ai = res_ai.data.decode('utf-8')
        self.assertIn('Power <span class="hero-headline-ai">AI</span>', html_ai)
        self.assertIn('marquee-bottom-container', html_ai)
        self.assertIn('全城极速抢单 (推荐·5分钟接单)', html_ai)
        self.assertIn('自选指定师傅', html_ai)
        self.assertIn('可以顺着下方步骤一步一步点选', html_ai)

        # 2. 模拟客户以 broadcast 提交全城抢单
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9998
            sess['role'] = 'customer'
        res_order = self.client.post('/orders/new', data={
            'category': '燃气灶',
            'new_device_model': '老板防干烧聚能燃气灶',
            'description': '[打不着火] 旋钮点火无火花且有燃气气味',
            'appointment_date': '2026-10-08',
            'appointment_slot': '上午 (10:00 - 12:00)',
            'contact_name': '李女士',
            'contact_phone': '13812345678',
            'service_address': '北京市朝阳区望京SOHO T3',
            'selected_tech_id': 'broadcast'
        }, follow_redirects=True)
        self.assertEqual(res_order.status_code, 200)

        # 3. 验证数据库中工单状态为 PENDING 且 technician_id 为空
        wo = WorkOrder.query.filter_by(description='[打不着火] 旋钮点火无火花且有燃气气味').first()
        self.assertIsNotNone(wo)
        self.assertEqual(wo.status, 'PENDING')
        self.assertIsNone(wo.technician_id)

        # 4. 获取两个 active 技师
        techs = Technician.query.filter_by(active=True).all()
        self.assertGreaterEqual(len(techs), 2)
        tech1, tech2 = techs[0], techs[1]

        # 5. 技师 1 查看工作台抢单池
        with self.client.session_transaction() as sess:
            sess['role'] = 'technician'
            sess['current_tech_id'] = tech1.id
        res_tech_pool = self.client.get('/tech')
        self.assertEqual(res_tech_pool.status_code, 200)
        self.assertIn('邻里抢单雷达', res_tech_pool.data.decode('utf-8'))

        # 6. 技师 1 触发抢单
        res_grab1 = self.client.post(f'/tech/{wo.id}/grab', follow_redirects=True)
        self.assertEqual(res_grab1.status_code, 200)
        self.assertIn('抢单成功', res_grab1.data.decode('utf-8'))

        # 重新从数据库拉取，验证工单已被 tech1 锁定
        db.session.refresh(wo)
        self.assertEqual(wo.status, 'ASSIGNED')
        self.assertEqual(wo.technician_id, tech1.id)

        # 7. 技师 2 紧接着并发抢同一张工单 -> 必须被优雅拦截
        with self.client.session_transaction() as sess:
            sess['role'] = 'technician'
            sess['current_tech_id'] = tech2.id
        res_grab2 = self.client.post(f'/tech/{wo.id}/grab', follow_redirects=True)
        self.assertEqual(res_grab2.status_code, 200)
        self.assertIn('该单已被其他师傅抢先一步接走啦', res_grab2.data.decode('utf-8'))

        # 工单依然完好归属于 tech1
        db.session.refresh(wo)
        self.assertEqual(wo.technician_id, tech1.id)

        # 清理测试数据
        db.session.delete(wo)
        db.session.commit()

    def test_checkin_code_anti_cheat_and_customer_rating_closure(self):
        """测试不可伪造核销码防跑单到场存证、钱包解冻与客户1~5星完工评价闭环"""
        # 1. 模拟客户发单，平台前置托管上门费
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9997
            sess['role'] = 'customer'
        res_order = self.client.post('/orders/new', data={
            'category': '热水器',
            'new_device_model': '万家乐恒温燃气热水器',
            'description': '[点火报错E1] 开启热水阀风机运转但无法点火',
            'contact_name': '陈先生',
            'contact_phone': '13799998888',
            'service_address': '海淀区知春路48号院',
            'selected_tech_id': 'broadcast'
        }, follow_redirects=True)
        self.assertEqual(res_order.status_code, 200)

        wo = WorkOrder.query.filter_by(description='[点火报错E1] 开启热水阀风机运转但无法点火').first()
        self.assertIsNotNone(wo)
        self.assertIsNotNone(wo.checkin_code)
        self.assertEqual(len(wo.checkin_code), 6)

        # 2. 技师接单
        tech = Technician.query.filter_by(active=True).first()
        self.assertIsNotNone(tech)
        initial_balance = tech.balance or 0.0

        with self.client.session_transaction() as sess:
            sess['role'] = 'technician'
            sess['current_tech_id'] = tech.id
        res_grab = self.client.post(f'/tech/{wo.id}/grab', follow_redirects=True)
        self.assertEqual(res_grab.status_code, 200)

        # 3. 客户在详情页查看滴滴式到达雷达与防跑单核销卡片
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9997
            sess['role'] = 'customer'
            sess['customer_id'] = wo.customer_id
        res_detail = self.client.get(f'/orders/{wo.id}')
        self.assertEqual(res_detail.status_code, 200)
        html_detail = res_detail.data.decode('utf-8')
        self.assertIn('智修云调度雷达定位中', html_detail)
        self.assertIn('不可伪造到场证明', html_detail)
        self.assertIn(wo.checkin_code, html_detail)

        # 4. 师傅上门防作弊校验：输入错误核销码必须被拦截
        with self.client.session_transaction() as sess:
            sess['role'] = 'technician'
            sess['current_tech_id'] = tech.id
        res_wrong_code = self.client.post(f'/tech/{wo.id}/checkin', data={'checkin_code': '000000'}, follow_redirects=True)
        self.assertEqual(res_wrong_code.status_code, 200)
        self.assertIn('核销码错误', res_wrong_code.data.decode('utf-8'))
        
        # 5. 师傅输入正确 6 位核销码 -> 到场核销打卡成功，出工费解冻至钱包
        res_correct_code = self.client.post(f'/tech/{wo.id}/checkin', data={'checkin_code': wo.checkin_code}, follow_redirects=True)
        self.assertEqual(res_correct_code.status_code, 200)
        self.assertIn('现场核销成功', res_correct_code.data.decode('utf-8'))

        db.session.refresh(wo)
        db.session.refresh(tech)
        self.assertIsNotNone(wo.checkin_at)
        self.assertEqual(wo.status, 'IN_PROGRESS')
        self.assertEqual(wo.pay_status, 'SETTLED')
        self.assertEqual(tech.balance, initial_balance + 25.0)

        # 6. 师傅现场检修完成，提交完工 -> 流转为 WAIT_CONFIRM
        res_finish = self.client.post(f'/tech/{wo.id}/offline-finish', data={
            'result_type': 'fixed',
            'note': '清理燃气喷嘴积碳，更换微动开关，测试出水温度正常'
        }, follow_redirects=True)
        self.assertEqual(res_finish.status_code, 200)

        db.session.refresh(wo)
        self.assertEqual(wo.status, 'WAIT_CONFIRM')

        # 7. 客户给师傅打 5 星好评并确认完结 -> 工单 CLOSED
        with self.client.session_transaction() as sess:
            sess['user_id'] = 9997
            sess['role'] = 'customer'
            sess['customer_id'] = wo.customer_id
        res_rate = self.client.post(f'/orders/{wo.id}/rate', data={
            'rating': '5',
            'rating_tags': '准时守约,专业熟练,无乱收费',
            'rating_comment': '师傅上门速度极快，20分钟就解决了打不着火的问题！'
        }, follow_redirects=True)
        self.assertEqual(res_rate.status_code, 200)

        db.session.refresh(wo)
        self.assertEqual(wo.status, 'CLOSED')
        self.assertEqual(wo.rating, 5)
        self.assertIn('准时守约', wo.rating_tags)
        self.assertIsNotNone(wo.rated_at)

        # 清理测试数据
        db.session.delete(wo)
        db.session.commit()





def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExtendedFeatures)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    count = result.testsRun
    if result.wasSuccessful():
        print(f"\n全部 {count} 项企业扩展与自研组件库断言通过 [OK]")
        return 0
    else:
        print(f"\n测试存在失败项: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
