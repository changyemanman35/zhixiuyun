"""三端通用 AI 智能助手 (ASM Copilot) 离线双模引擎与专家知识库
严格遵守 NFR-6 纯离线原则：零外网依赖，毫秒级响应，内置隐私脱敏与三端专业知识库
"""
import re
from datetime import datetime


def sanitize_text(text):
    """敏感信息正则脱敏过滤器（保护客户隐私安全）"""
    if not text:
        return ""
    # 手机号脱敏：保留前3后4
    sanitized = re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)
    # 门牌号脱敏（如 302室、1号楼2单元）
    sanitized = re.sub(r'\d+号楼\d+单元\d+室?', '[详细门牌已脱敏]', sanitized)
    sanitized = re.sub(r'\d+室', '[门牌已脱敏]', sanitized)
    return sanitized


# 家电与数码常见故障专家知识库（基于海尔、苹果标准售后 SOP）
FAULT_EXPERT_KB = [
    {
        'keywords': ['不制冷', '吹热风', '制冷差', '不冷', '空调不凉'],
        'fault_name': '空调制冷系统故障',
        'possible_causes': ['制冷剂泄漏/不足', '四通阀串气', '室外冷凝器积灰过厚', '压缩机启动电容失效'],
        'emergency_action': '建议先清洗室内机滤网，检查室外机风扇是否转动；若吹出常温风请及时报修，避免压缩机长时间空转过热。',
        'recommended_parts': ['变频主板', '通用电容', '冷媒R410A'],
        'safety_warning': '检修冷媒压力与压缩机接线柱时，务必先切断总电源，严禁带电测量高压端！'
    },
    {
        'keywords': ['不开机', '无法开机', '黑屏', '不通电', '电源没反应', '开不了机'],
        'fault_name': '主板及供电模块故障',
        'possible_causes': ['开关电源板损坏', '输入保险丝熔断', '主控板核心芯片短路', '电源插座接触不良'],
        'emergency_action': '请先更换可用插座排查供电电源；若有焦糊味，请立即拔下电源插头并断开空气开关！',
        'recommended_parts': ['电源适配器', '变频主板', '通用保险管'],
        'safety_warning': '开关电源高压滤波电容在断电后仍有数百伏残存电压，检修前必须用大功率电阻进行安全放电！'
    },
    {
        'keywords': ['漏水', '渗水', '积水', '排水不畅'],
        'fault_name': '排水及管路渗漏故障',
        'possible_causes': ['冷凝水排水管折弯或堵塞', '室内机集水盘开裂破损', '管道保温棉破损结露'],
        'emergency_action': '在漏水处下方放置接水容器，关闭设备运行，切勿让水滴溅入插座或墙壁接线盒。',
        'recommended_parts': ['加厚排水管', '专用集水弯'],
        'safety_warning': '水汽潮湿环境下极易发生漏电，排查时禁止湿手触碰电器外壳。'
    },
    {
        'keywords': ['e1', 'e2', 'e3', 'e6', '故障码', '代码'],
        'fault_name': '传感器或通信总线异常',
        'possible_causes': ['室内外机通讯线缆虚接', '管温/环温传感器阻值漂移', '室外机散热不良高压保护'],
        'emergency_action': '尝试将总电源断电 5 分钟后重新上电复位；若依然显示代码，说明硬件传感器需技师测量。',
        'recommended_parts': ['温度传感器探头', '变频主控板'],
        'safety_warning': '排查室内外连机线时，请使用万用表交流档确认无感应电压后再进行接线。'
    },
    {
        'keywords': ['异响', '噪音', '震动大', '轰鸣', '刺耳'],
        'fault_name': '电机风扇与机械组件故障',
        'possible_causes': ['贯流风扇轴承磨损卡死', '风轮异物卡阻', '压缩机减震脚垫老化开裂'],
        'emergency_action': '立即关机，防止风轮卡阻烧毁电机绕组。',
        'recommended_parts': ['直流风机电机', '减震橡胶垫'],
        'safety_warning': '旋转部件在惯性停转前严禁将手伸入风道内部。'
    },
    {
        'keywords': ['洗衣机', '不脱水', '撞桶', '脱水震动', '不转'],
        'fault_name': '洗衣机传动与平衡脱水故障',
        'possible_causes': ['内桶减震阻尼吊杆老化失衡', '离合器棘爪磨损打滑', '水位传感器管路漏气', '电机启动电容容量衰减'],
        'emergency_action': '暂停洗衣程序，检查桶内衣物是否单侧偏重；若重新整理后依然撞桶异响，请申请专业更换阻尼器。',
        'recommended_parts': ['加厚阻尼吊杆(4根套)', '原厂离合器总成', '水位传感器'],
        'safety_warning': '高速旋转脱水桶具有极高惯性冲量，安全门锁解除前绝对禁止强行开盖探手！'
    },
    {
        'keywords': ['热水器', '不打火', '不出热水', '点不着', '水不热', '打不着火'],
        'fault_name': '燃气热水器燃烧与点火总成故障',
        'possible_causes': ['水气联动阀微动开关接触不良', '高压点火针积碳绝缘不良', '比例阀线圈开路或供气不足', '热交换水箱结垢老化'],
        'emergency_action': '首先确认燃气总阀已开且电池电量充足；若有明显燃气异味，立即开窗通风，严禁使用明火或启闭电器！',
        'recommended_parts': ['双针脉冲点火器', '水气联动微动开关', '原厂燃气比例阀'],
        'safety_warning': '燃气管路及燃烧室检修属于国家特种作业范畴，严禁非持证人员自行拆卸气阀接口！'
    },
    {
        'keywords': ['冰箱', '结冰', '结霜', '冷冻室结冰', '化霜'],
        'fault_name': '冰箱制冷循环与化霜系统故障',
        'possible_causes': ['化霜定时器损坏或主板化霜继电器触点烧结', '蒸发器化霜电热管烧断开路', '门封磁条老化开裂漏气', '排水孔被冰晶封堵'],
        'emergency_action': '将冰箱断电 4 小时进行人工化霜，切勿使用锋利金属刀具敲击内胆或蒸发器铜铝管！',
        'recommended_parts': ['化霜石英加热管', '除霜温控器', '加厚磁性门封胶条'],
        'safety_warning': '蒸发器管壁极薄（铝合金厚度仅0.6mm），利器敲击会导致制冷剂瞬间喷发报废！'
    },
    {
        'keywords': ['油烟机', '吸力小', '倒灌', '油烟抽不走', '排烟差'],
        'fault_name': '吸油烟机动力风道与止回阀故障',
        'possible_causes': ['公共烟道防火止回阀叶片油泥卡死', '多翼离心风轮重度积油动平衡失调', '排风软管弯折挤压截面积缩小', '电机启动电容老化衰减'],
        'emergency_action': '先排查厨房外窗是否留有进风补气缝隙；定期深度清洗风轮，避免风机电机长期过载堵转烧毁。',
        'recommended_parts': ['防倒灌密闭止回阀', '低噪全封闭交流电机', '耐高温排烟铝箔波纹管'],
        'safety_warning': '清洗烟机叶轮时务必断开电源插座，防止误触触摸屏导致电机骤然启动切伤手指！'
    }
]


def process_copilot_chat(user_prompt, role, context_page, user_id, db_session, history=None):
    """三端通用 AI 智能助手主处理引擎（支持双模架构：离线保底 + 外部扩展 + 多轮上下文记忆）"""
    from models import AIChatLog, WorkOrder, Part, Technician, Customer

    raw_text = (user_prompt or "").strip()
    sanitized_prompt = sanitize_text(raw_text)
    lower_text = raw_text.lower()

    # 提取多轮历史中的上下文故障与设备信息
    last_fault_item = None
    if history:
        for h in reversed(history):
            h_text = (h.get('content') or '').lower()
            for item in FAULT_EXPERT_KB:
                if item['fault_name'].lower() in h_text or any(kw in h_text for kw in item['keywords']):
                    last_fault_item = item
                    break
            if last_fault_item:
                break

    # 1. 意图分类器 (Intent Classifier，结合多轮上下文)
    intent = 'general'
    actions = []
    suggestions = []

    # 价格与收费追问 (多轮上下文核心)
    if any(k in lower_text for k in ['多少钱', '费用', '价格', '贵不贵', '收费', '价目', '预算', '修要多少', '收多少']):
        intent = 'pricing'
    # 上门时效追问
    elif any(k in lower_text for k in ['多久能来', '什么时候来', '几点上门', '今天能到', '快点', '上门时效', '几时来']):
        intent = 'dispatch_sla'
    # 质保与发票追问
    elif any(k in lower_text for k in ['保修多久', '质保', '发票', '质保期', '保修期', '开发票', '收据']):
        intent = 'warranty_policy'
    # 巡检/看板 (调度员视角)
    elif any(k in lower_text for k in ['看板', '超时', '加急', '巡检', '负荷', '库存告急', '好评', '考勤', '待办']):
        intent = 'inspect'
    # 技师排障/测量/SOP (技师视角)
    elif any(k in lower_text for k in ['测量', '阻值', 'sop', '引脚', '接线', '拆机', '电路图', '高压']) or role == 'technician':
        intent = 'troubleshoot'
    # 查单 (客户视角)
    elif any(k in lower_text for k in ['查单', '进度', '工单', '修好了吗', '我的单', '单号']) or ('wo-' in lower_text):
        intent = 'query_order'
    # 故障诊断 (客户报修导诊)
    elif any(any(kw in lower_text for kw in item['keywords']) for item in FAULT_EXPERT_KB) or any(k in lower_text for k in ['坏了', '故障', '修', '怎么回事']):
        intent = 'diagnose'

    # 2. 根据意图与角色组装大厂级专家回答
    reply_lines = []

    if intent == 'pricing':
        fault_name = last_fault_item['fault_name'] if last_fault_item else '家电综合检修'
        parts_str = ('、'.join(last_fault_item['recommended_parts'])) if last_fault_item else '原厂正品备件'
        reply_lines.append(f"### 💰 官方透明计价与费用预估报告")
        reply_lines.append(f"结合上下文针对您咨询的 **【{fault_name}】**：")
        reply_lines.append(f"1. **官方上门检测费**：基础故障诊断仅 **¥30 起**（师傅上门核实，若现场动工则全额抵扣维修费）；")
        reply_lines.append(f"2. **保内政策**：若您的设备在官方质保期内，经技术核验后**配件费与工时费均为 ¥0.00**；")
        reply_lines.append(f"3. **备件参考单价**：建议更换的备件（`{parts_str}`）严格执行官方备件库指导价（约 ¥35~120/件，系统快照锁定，拒绝加价）；")
        reply_lines.append(f"\n> 💡 **安心承诺**：维修全程透明报价，客户签字同意后再作业，修好再付款，拒绝乱收费。")
        actions.append({
            'label': '⚡ 一键直接报修 (免填单极速派工)',
            'url': f'/portal?fault={fault_name}&desc={raw_text}',
            'primary': True
        })
        suggestions = ["维修后配件保修多久？", "今天预约师傅几点能上门？", "支持开具发票吗？"]

    elif intent == 'dispatch_sla':
        reply_lines.append(f"### ⏱️ 官方响应时效与极速派工承诺")
        reply_lines.append(f"1. **15 分钟极速响应**：报修提交后，调度中心智能算法将向周边 3 公里内持证工程师秒级派单；")
        reply_lines.append(f"2. **2 小时极速上门**：支持紧急加急预约，工程师接单后会立即电话联系您确认具体上门时段；")
        reply_lines.append(f"3. **服务覆盖**：周一至周日 8:00~21:00 全天候无休保障，恶劣天气不加收上门附加费。")
        actions.append({
            'label': '⚡ 立即派工预约师傅',
            'url': '/portal',
            'primary': True
        })
        suggestions = ["费用大概是多少？", "配件有保障吗？", "支持开具增值税发票吗？"]

    elif intent == 'warranty_policy':
        reply_lines.append(f"### 🛡️ 官方配件质保与发票权益")
        reply_lines.append(f"1. **原厂备件 90 天质保**：所有经官方认证工程师更换的正品备件，均享受 **90 天官方全国联保**（质保期内同类故障免费复检包换）；")
        reply_lines.append(f"2. **电子工单存证**：完工后自动生成可追溯的电子工单与流水明细，终身存档可查；")
        reply_lines.append(f"3. **正规发票**：支持开具企业或个人增值税电子普通发票/专用发票，报销无忧。")
        actions.append({
            'label': '⚡ 一键直接报修',
            'url': '/portal',
            'primary': True
        })
        suggestions = ["修一下大概多少钱？", "预约师傅今天能来吗？", "附近有哪些网点？"]

    elif intent == 'diagnose':
        # 匹配知识库
        matched = None
        for item in FAULT_EXPERT_KB:
            if any(kw in lower_text for kw in item['keywords']):
                matched = item
                break
        if not matched:
            matched = FAULT_EXPERT_KB[0]  # 默认制冷/通用

        reply_lines.append(f"### 🔍 AI 故障预诊断分析报告")
        reply_lines.append(f"**初步判定分类**：`{matched['fault_name']}`")
        reply_lines.append(f"\n**可能的核心原因**：")
        for idx, c in enumerate(matched['possible_causes'], 1):
            reply_lines.append(f"{idx}. {c}")
        reply_lines.append(f"\n> 💡 **应急处理指引**：{matched['emergency_action']}")
        reply_lines.append(f"\n⚠️ **安全警示**：{matched['safety_warning']}")
        
        actions.append({
            'label': '📝 一键代填官方报修单',
            'url': f'/portal?fault={matched["fault_name"]}&desc={raw_text}',
            'primary': True
        })
        suggestions = ["平台如何保障上门费安全？", "附近师傅多久能接单？", "预约技师上门流程是什么？"]

    elif intent == 'query_order':
        # 查单逻辑
        order = None
        # 尝试提取工单号
        wo_match = re.search(r'WO-\d{8}-\d{4}', raw_text, re.IGNORECASE)
        if wo_match:
            order = db_session.query(WorkOrder).filter_by(order_no=wo_match.group(0).upper()).first()
        else:
            # 查找该用户最新工单
            if user_id:
                order = db_session.query(WorkOrder).order_by(WorkOrder.created_at.desc()).first()

        if order:
            from config import STATUS_LABELS_CUSTOMER
            status_text = STATUS_LABELS_CUSTOMER.get(order.status, order.status)
            reply_lines.append(f"### 📦 找到您的工单：`{order.order_no}`")
            reply_lines.append(f"- **服务设备**：{order.device.model if order.device else '官方设备'}")
            reply_lines.append(f"- **当前进度**：**{status_text}**")
            reply_lines.append(f"- **报修日期**：{order.created_at.strftime('%Y-%m-%d %H:%M')}")
            if order.appointment_slot:
                reply_lines.append(f"- **预约时段**：`{order.appointment_date or '已预约'} {order.appointment_slot}`")
            if order.technician:
                reply_lines.append(f"- **派工技师**：{order.technician.name} 师傅")
            
            actions.append({
                'label': '🔍 查看工单全景时间线',
                'url': f'/query?order_no={order.order_no}',
                'primary': True
            })
        else:
            reply_lines.append("### 🔍 工单查询助手")
            reply_lines.append("未直接检索到关联工单。您可以提供 **工单号（如 WO-20261001-0001）** 或手机号，我将立即为您检索最新维修进度与预计到达时段。")
            actions.append({
                'label': '进入全功能客户查单大厅',
                'url': '/query',
                'primary': True
            })
        suggestions = ["查一下今天的加急工单", "空调报修多久能上门？", "官方收费标准是怎样的？"]

    elif intent == 'troubleshoot':
        matched = None
        for item in FAULT_EXPERT_KB:
            if any(kw in lower_text for kw in item['keywords']):
                matched = item
                break
        if not matched:
            matched = FAULT_EXPERT_KB[3]  # 传感器/主板排查

        reply_lines.append(f"### 🛠️ 工程师现场排障 SOP 手册")
        reply_lines.append(f"**排查针对项目**：`{matched['fault_name']}`")
        reply_lines.append(f"\n**推荐排障步骤**：")
        reply_lines.append(f"1. **静态断电测量**：使用数字万用表欧姆档测量主板阻值，确认无对地击穿短路；")
        reply_lines.append(f"2. **上电动态检测**：测试开关电源输出 12V、5V 直流基准电压是否纹波稳定；")
        reply_lines.append(f"3. **通信波形排查**：测量室内外机通讯端子之间是否存在 DC 24~48V 脉动跳变信号；")
        reply_lines.append(f"\n📦 **建议申请原厂备件**：{', '.join(matched['recommended_parts'])}")
        reply_lines.append(f"\n⚡ **安全红线**：{matched['safety_warning']}")
        
        actions.append({
            'label': '进入技师工作台',
            'url': '/tech',
            'primary': True
        })
        suggestions = ["变频主板通讯E6排查手册", "测量传感器阻值标准", "更换压缩机安全指引"]

    elif intent == 'inspect':
        # Text-to-Insight 调度统计
        urgent_count = db_session.query(WorkOrder).filter(
            WorkOrder.priority == 'urgent',
            WorkOrder.status.in_(['PENDING', 'ASSIGNED', 'IN_PROGRESS'])
        ).count()
        
        pending_count = db_session.query(WorkOrder).filter(WorkOrder.status == 'PENDING').count()
        low_stock_parts = db_session.query(Part).filter(Part.stock_quantity <= Part.min_stock_alert).all()

        reply_lines.append(f"### 📊 运营看板智能巡检简报 (Text-to-Insight)")
        reply_lines.append(f"- **待分配派工单 (PENDING)**：`{pending_count}` 张")
        reply_lines.append(f"- **当前在途加急单 (URGENT)**：`{urgent_count}` 张 {'🔥 需重点监控' if urgent_count > 0 else '✅ 负荷正常'}")
        
        if low_stock_parts:
            reply_lines.append(f"\n⚠️ **备件库存告急预警** ({len(low_stock_parts)} 项低于安全阈值)：")
            for p in low_stock_parts[:3]:
                reply_lines.append(f"  - `{p.name}`：当前仅剩 **{p.stock_quantity}** 件 (安全下限: {p.min_stock_alert})")
        else:
            reply_lines.append("\n✅ **物料库存**：所有原厂配件均处于安全库存水位以上。")

        actions.append({
            'label': '前往调度大屏看板',
            'url': '/',
            'primary': True
        })
        suggestions = ["今日有哪些超时单？", "当前哪些配件库存告急？", "技师好评率榜单"]

    else:
        # 通用回答
        reply_lines.append("### 👋 您好！我是家电快修智能下单助手 (AI Copilot)")
        reply_lines.append("我可以帮您 **30秒极速提取故障并呼叫附近维修师**：")
        reply_lines.append("- **一句话极速下单**：直接告诉我您的电器品牌、故障表现、上门时间与门牌地址；")
        reply_lines.append("- **平台安全托管**：¥30 基础排查上门费由平台安全托管，师傅上门打卡后解冻；")
        reply_lines.append("- **线下透明议价**：具体机器维修方案与配件费，由您与工程师在现场自由协商，修不好或不修无额外费用。")
        actions.append({
            'label': '⚡ 立即通过 AI 极速报修 (预付¥30上门费)',
            'url': '/orders/new',
            'primary': True
        })
        suggestions = ["我家海尔洗衣机不排水，明天下午有空", "格力空调开机只吹风不制冷", "热水器打不着火，能尽快来修吗？"]

    reply_markdown = "\n".join(reply_lines)

    # 3. 记录 AIChatLog 审计
    try:
        log = AIChatLog(
            user_id=user_id,
            role=role or 'guest',
            user_prompt=raw_text,
            sanitized_prompt=sanitized_prompt,
            ai_response=reply_markdown,
            intent_detected=intent,
            engine_used='local_expert'
        )
        db_session.add(log)
        db_session.commit()
    except Exception:
        db_session.rollback()

    return {
        'reply': reply_markdown,
        'intent': intent,
        'suggestions': suggestions,
        'actions': actions
    }


def extract_order_copilot(text):
    """从自然语言中高精提取 C2C 下单结构化要素"""
    if not text:
        return {}

    raw = text.strip()
    result = {
        'category': '',
        'brand': '',
        'device_model': '',
        'symptom': '',
        'expected_time': '',
        'address': '',
        'phone': ''
    }

    # 1. 品类识别
    categories = ['空调', '冰箱', '洗衣机', '热水器', '油烟机', '燃气灶', '电视', '微波炉', '净水器', '洗碗机', '壁挂炉', '小家电']
    for cat in categories:
        if cat in raw:
            result['category'] = cat
            break

    # 2. 品牌识别
    brands = ['格力', '美的', '海尔', '西门子', '容声', '奥克斯', '创维', 'TCL', '小米', '老板', '方太', '松下', '索尼', '海信', '飞利浦', '卡萨帝', '统帅']
    for b in brands:
        if b in raw:
            result['brand'] = b
            break

    # 组合为完整型号标签
    if result['brand'] and result['category']:
        result['device_model'] = f"{result['brand']} {result['category']}"
    elif result['category']:
        result['device_model'] = f"家用 {result['category']}"
    elif result['brand']:
        result['device_model'] = f"{result['brand']} 智能电器"
    else:
        result['device_model'] = "家用电器"

    # 3. 提取手机号 (1开头的11位手机号)
    phone_match = re.search(r'1[3-9]\d{9}', raw)
    if phone_match:
        result['phone'] = phone_match.group(0)

    # 4. 提取时间
    time_matches = []
    time_keywords = ['今天', '明天', '后天', '周一', '周二', '周三', '周四', '周五', '周六', '周日', '上午', '下午', '晚上', '立刻', '马上']
    for kw in time_keywords:
        if kw in raw:
            time_matches.append(kw)
    clock_match = re.search(r'(\d{1,2}[点时:](\d{1,2})?)', raw)
    if clock_match:
        time_matches.append(clock_match.group(0))
    if time_matches:
        result['expected_time'] = " ".join(time_matches)
    else:
        result['expected_time'] = "尽快上门 (今天/明天)"

    # 5. 提取地址 (省市区县/路/街道/小区/号院/楼栋室)
    addr_match = re.search(r'(?:在|于|地址[为是:：]?)?([\u4e00-\u9fa5]{2,6}(?:省|市|区|县)[\u4e00-\u9fa50-9A-Za-z\-#号院楼单元室弄街道路巷小区花园家园]+)', raw)
    if not addr_match:
        addr_match = re.search(r'([\u4e00-\u9fa50-9A-Za-z\-#]+(?:路|街|道|小区|花园|家园|大厦|栋|号楼|单元|室)[0-9A-Za-z\-#室单元楼号]*)', raw)
    if addr_match:
        addr_str = addr_match.group(1) if addr_match.lastindex else addr_match.group(0)
        for prefix in ['我在', '在', '于', '地址是', '地址为', '地址：', '地址:']:
            if addr_str.startswith(prefix):
                addr_str = addr_str[len(prefix):]
        result['address'] = addr_str.strip()
    else:
        result['address'] = ""

    # 6. 提取故障表象
    symptom_candidates = ['不制冷', '不排水', '不加热', '漏水', '无法开机', '打不着火', '异响', '抖动剧烈', '吹热风', '黑屏', '冒烟', '跳闸', '不通电', '结冰严重', '吸力变弱']
    found_symptoms = [s for s in symptom_candidates if s in raw]
    if found_symptoms:
        result['symptom'] = "、".join(found_symptoms)
    else:
        # 去掉识别出来的地址、电话后作为描述
        cleaned = raw
        if result['phone']:
            cleaned = cleaned.replace(result['phone'], '')
        if result['address']:
            cleaned = cleaned.replace(result['address'], '')
        result['symptom'] = cleaned[:100].strip() or "待师傅上门现场检测"

    return result
