import os
import cv2
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFont

def create_home_repair_movie():
    width = 1280
    height = 720
    fps = 30
    duration_sec = 4
    total_frames = fps * duration_sec  # 120 帧
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frames_dir = os.path.join(base_dir, 'static', 'frames', 'home_repair')
    video_path = os.path.join(base_dir, 'static', 'videos', 'home_appliance_repair.mp4')
    
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_out = cv2.VideoWriter(video_path, fourcc, float(fps), (width, height))
    
    print(f"正在生成真实民生家电维修电影级推轨序列帧 (共 {total_frames} 帧)...")
    
    # 尝试加载常用中文字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",   # 黑体
        "C:/Windows/Fonts/simsun.ttc",   # 宋体
        "C:/Windows/Fonts/arial.ttf"
    ]
    font_main = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_title = ImageFont.truetype(fp, 36)
                font_sub = ImageFont.truetype(fp, 22)
                font_badge = ImageFont.truetype(fp, 18)
                font_stamp = ImageFont.truetype(fp, 24)
                break
            except Exception:
                continue
    if font_main is None:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_stamp = ImageFont.load_default()

    for idx in range(total_frames):
        t = idx / (total_frames - 1)  # 0.0 -> 1.0 进度
        
        # ── 1. 真实温馨居家客厅背景 (温暖米白与阳光柔和漫射) ──
        # 模拟自然景深与相机推轨 (Dolly-in Zoom: 1.0 -> 1.45)
        zoom = 1.0 + 0.45 * t
        
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 背景墙壁温馨米白渐变
        # 随着镜头推近，暖阳漫射加深
        wall_y = np.linspace(0, 1, height)[:, None]
        wall_color = (
            np.clip(242 - 15 * t + 8 * np.sin(wall_y * 3.14), 220, 255),  # B
            np.clip(246 - 10 * t + 12 * np.sin(wall_y * 3.14), 225, 255), # G
            np.clip(252 - 5 * t + 15 * np.sin(wall_y * 3.14), 235, 255)   # R (暖调)
        )
        img[:, :] = np.dstack(wall_color).astype(np.uint8)
        
        # 木质地板 (底部 200px 随推轨而下沉)
        floor_top = int(height * (0.72 + 0.08 * t))
        for y in range(floor_top, height):
            depth_ratio = (y - floor_top) / max(1, height - floor_top)
            # 暖木纹色 (BGR: 50~70, 95~125, 160~190)
            fb = int(55 + 20 * depth_ratio)
            fg = int(100 + 25 * depth_ratio)
            fr = int(168 + 22 * depth_ratio)
            img[y, :] = (fb, fg, fr)
        # 地板踢脚线
        cv2.line(img, (0, floor_top), (width, floor_top), (35, 60, 110), 3)

        # 落地窗自然采光柔光斜射 (左侧柔光束)
        window_pts = np.array([[0, 0], [int(width * 0.45 - 60 * t), 0], [int(width * 0.25 - 40 * t), height], [0, height]], np.int32)
        overlay_light = img.copy()
        cv2.fillPoly(overlay_light, [window_pts], (255, 255, 240))
        cv2.addWeighted(overlay_light, 0.18, img, 0.82, 0, img)
        
        # 室内绿植 (左下角点缀生活温馨感)
        plant_x = int(90 - 40 * t)
        plant_y = floor_top - 20
        cv2.circle(img, (plant_x, plant_y), 45, (60, 120, 40), -1)
        cv2.circle(img, (plant_x + 30, plant_y - 25), 35, (75, 140, 50), -1)
        cv2.circle(img, (plant_x - 20, plant_y - 15), 30, (50, 110, 35), -1)

        # ── 2. 家电主体（客厅变频智能空调·随镜头平稳推移聚焦）──
        # 空调中心坐标与尺度
        ac_w = int(580 * zoom)
        ac_h = int(220 * zoom)
        ac_cx = width // 2
        # 相机推轨运动：视角逐渐下移聚焦到师傅维修工作台面
        ac_cy = int(240 - 70 * t)
        
        ac_x1 = ac_cx - ac_w // 2
        ac_y1 = ac_cy - ac_h // 2
        ac_x2 = ac_cx + ac_w // 2
        ac_y2 = ac_cy + ac_h // 2
        
        # 空调阴影 (柔和环境光遮蔽)
        cv2.rectangle(img, (ac_x1 + 10, ac_y1 + 15), (ac_x2 + 15, ac_y2 + 25), (190, 195, 205), -1)
        
        # 空调主体纯白优雅机身
        cv2.rectangle(img, (ac_x1, ac_y1), (ac_x2, ac_y2), (248, 248, 250), -1)
        # 金属香槟金装饰边框
        cv2.rectangle(img, (ac_x1, ac_y1), (ac_x2, ac_y2), (180, 200, 215), 2)
        cv2.line(img, (ac_x1, ac_y2 - 25), (ac_x2, ac_y2 - 25), (160, 185, 205), 2)

        # ── 3. 随滚轮演进的 4 幕真实家电维修场景 ──
        # 阶段 1: t < 0.28   (故障待检·生活纪实·常态出风口异常提示)
        # 阶段 2: 0.28<=t<0.6 (师傅佩戴鞋套进门·铺防尘垫·展开专业工具箱与检测仪)
        # 阶段 3: 0.6<=t<0.85 (专业拆盖深层蒸汽清洗保养·原厂配件精准更换)
        # 阶段 4: t >= 0.85  (机器复原如新·平稳清新送风·出具90天官方质保凭证)

        # 阶段 1 视觉元素
        if t < 0.35:
            # 导风板常态微开，LED 故障指示灯微闪 (橙黄色故障提醒)
            louver_y = ac_y2 - 18
            cv2.line(img, (ac_x1 + 40, louver_y), (ac_x2 - 40, louver_y), (210, 210, 215), 6)
            # LED 状态屏：26℃ 待检修闪烁
            led_x = ac_x2 - int(120 * zoom)
            led_y = ac_cy - 10
            cv2.rectangle(img, (led_x, led_y), (led_x + 60, led_y + 35), (35, 35, 38), -1)
            cv2.circle(img, (led_x + 18, led_y + 18), 5, (0, 140, 255), -1) # 橙色待修灯

        # 阶段 2 & 阶段 3 & 阶段 4：地面维修防尘垫与专业工具箱
        if t >= 0.20:
            tool_alpha = min(1.0, (t - 0.20) / 0.15)
            # 地面专业维修防尘垫 (深蓝带刻度专业地垫)
            pad_y1 = floor_top + 10
            pad_y2 = height - 15
            pad_w = int(720 * min(1.2, zoom))
            pad_x1 = (width - pad_w) // 2
            pad_x2 = pad_x1 + pad_w
            
            overlay_pad = img.copy()
            cv2.rectangle(overlay_pad, (pad_x1, pad_y1), (pad_x2, pad_y2), (120, 60, 20), -1) # 售后专用深蓝地垫
            cv2.rectangle(overlay_pad, (pad_x1, pad_y1), (pad_x2, pad_y2), (200, 160, 50), 3) # 警示包边
            cv2.addWeighted(overlay_pad, tool_alpha * 0.88, img, 1 - tool_alpha * 0.88, 0, img)
            
            # 专业技师多功能工具箱 (打开状态，整齐陈列)
            box_w = 260
            box_h = 130
            box_x = pad_x1 + 60
            box_y = pad_y1 + 35
            
            # 工具箱底座与金属卡扣
            cv2.rectangle(img, (box_x, box_y), (box_x + box_w, box_y + box_h), (45, 45, 50), -1)
            cv2.rectangle(img, (box_x, box_y), (box_x + box_w, box_y + box_h), (180, 180, 190), 2)
            # 黄黑防撞角
            for corner in [(box_x, box_y), (box_x + box_w - 20, box_y), (box_x, box_y + box_h - 20), (box_x + box_w - 20, box_y + box_h - 20)]:
                cv2.rectangle(img, corner, (corner[0] + 20, corner[1] + 20), (30, 180, 250), -1)
            
            # 箱内仪表：数字高精万用表 (黄黑专业款)
            cv2.rectangle(img, (box_x + 20, box_y + 20), (box_x + 90, box_y + 110), (20, 190, 245), -1)
            cv2.rectangle(img, (box_x + 30, box_y + 30), (box_x + 80, box_y + 60), (30, 30, 30), -1)
            # 万用表液晶屏点亮蓝光
            cv2.rectangle(img, (box_x + 34, box_y + 34), (box_x + 76, box_y + 56), (220, 200, 40), -1)
            # 红黑双色高压绝缘测试表笔
            cv2.line(img, (box_x + 50, box_y + 105), (box_x - 30, box_y + 140), (40, 40, 220), 3) # 红笔
            cv2.line(img, (box_x + 65, box_y + 105), (box_x - 15, box_y + 150), (20, 20, 20), 3)  # 黑笔
            
            # 螺丝刀组与原厂配件密封盒
            for si in range(4):
                cv2.line(img, (box_x + 115 + si * 18, box_y + 25), (box_x + 115 + si * 18, box_y + 105), (190, 190, 200), 4)
            # 原厂配件盒
            cv2.rectangle(img, (box_x + 195, box_y + 25), (box_x + 245, box_y + 105), (230, 230, 230), -1)
            cv2.rectangle(img, (box_x + 195, box_y + 25), (box_x + 245, box_y + 105), (0, 120, 220), 2)
            
            # 专业高压蒸汽深度清洗机 (右侧)
            cleaner_x = pad_x2 - 190
            cleaner_y = pad_y1 + 30
            cv2.rectangle(img, (cleaner_x, cleaner_y), (cleaner_x + 130, cleaner_y + 120), (235, 140, 30), -1) # 亮橙色工程机身
            cv2.rectangle(img, (cleaner_x, cleaner_y), (cleaner_x + 130, cleaner_y + 120), (180, 90, 10), 2)
            cv2.circle(img, (cleaner_x + 65, cleaner_y + 45), 22, (250, 250, 250), -1) # 压力指示表
            cv2.line(img, (cleaner_x + 65, cleaner_y + 45), (cleaner_x + 75, cleaner_y + 35), (20, 20, 220), 2) # 指针

        # 阶段 3: 专业拆检与深度清洗维护 (0.50 <= t < 0.85)
        if 0.45 <= t < 0.88:
            clean_phase = min(1.0, (t - 0.45) / 0.35)
            # 空调前面板规范向上掀开
            panel_lift = int(50 * clean_phase)
            cv2.rectangle(img, (ac_x1 + 30, ac_y1 - panel_lift), (ac_x2 - 30, ac_y1 + 40), (240, 240, 245), -1)
            cv2.rectangle(img, (ac_x1 + 30, ac_y1 - panel_lift), (ac_x2 - 30, ac_y1 + 40), (160, 185, 205), 2)
            
            # 露出的高密抑菌滤网与蒸发器翅片 (整洁银蓝光泽，绝非杂乱铜管)
            fin_x1 = ac_x1 + 45
            fin_y1 = ac_y1 + 25
            fin_x2 = ac_x2 - 45
            fin_y2 = ac_y2 - 35
            cv2.rectangle(img, (fin_x1, fin_y1), (fin_x2, fin_y2), (210, 225, 235), -1)
            # 规则细密蒸发器散热格栅线
            for gx in range(fin_x1 + 10, fin_x2 - 10, 15):
                cv2.line(img, (gx, fin_y1 + 5), (gx, fin_y2 - 5), (180, 205, 220), 1)
            
            # 清洗高压喷雾粒子动态流动 (蒸汽除菌雾气)
            spray_center_x = int(fin_x1 + (fin_x2 - fin_x1) * (0.3 + 0.4 * math.sin(t * 12)))
            spray_center_y = int(fin_y1 + 40)
            overlay_steam = img.copy()
            for r in range(12, 70, 14):
                cv2.circle(overlay_steam, (spray_center_x, spray_center_y), r, (255, 255, 255), -1)
            cv2.addWeighted(overlay_steam, 0.35, img, 0.65, 0, img)

        # 阶段 4: 试机运转，送风清爽，官方90天质保卡出具 (t >= 0.80)
        if t >= 0.78:
            finish_phase = min(1.0, (t - 0.78) / 0.22)
            # 空调恢复完整合盖，导风板优雅下探送风
            louver_y = ac_y2 - 5
            cv2.line(img, (ac_x1 + 30, louver_y), (ac_x2 - 30, louver_y + 15), (230, 230, 235), 8)
            
            # 强劲清爽健康柔风流线 (蓝白色优雅弧线飘动)
            wind_alpha = finish_phase * 0.8
            overlay_wind = img.copy()
            for wi in range(6):
                w_offset = int(wi * 35 + (idx * 8) % 40)
                curve_pts = [
                    (ac_x1 + 80 + wi * 80, louver_y + 15),
                    (ac_x1 + 100 + wi * 85, louver_y + 80),
                    (ac_x1 + 70 + wi * 90 - w_offset, louver_y + 170)
                ]
                pts = np.array(curve_pts, np.int32).reshape((-1, 1, 2))
                cv2.polylines(overlay_wind, [pts], False, (255, 235, 180), 3, cv2.LINE_AA)
            cv2.addWeighted(overlay_wind, wind_alpha, img, 1 - wind_alpha, 0, img)
            
            # LED 屏亮起健康的冰蓝 24℃
            led_x = ac_x2 - int(120 * zoom)
            led_y = ac_cy - 10
            cv2.rectangle(img, (led_x, led_y), (led_x + 60, led_y + 35), (20, 20, 25), -1)
            cv2.circle(img, (led_x + 18, led_y + 18), 5, (230, 200, 30), -1) # 绿色运转指示灯

            # 前景中央右侧：官方90天质保卡与明码公证书 (信赖感拉满)
            card_w = 420
            card_h = 240
            card_x = width - card_w - int(50 * finish_phase)
            card_y = int(height * 0.28)
            
            # 质保卡卡体 (白金轻奢防伪底纹)
            cv2.rectangle(img, (card_x + 8, card_y + 8), (card_x + card_w + 8, card_y + card_h + 8), (170, 175, 185), -1) # 阴影
            cv2.rectangle(img, (card_x, card_y), (card_x + card_w, card_y + card_h), (255, 255, 255), -1)
            cv2.rectangle(img, (card_x, card_y), (card_x + card_w, card_y + card_h), (50, 160, 235), 3) # 金牌金边
            
            # 顶部官方售后金盾抬头条
            cv2.rectangle(img, (card_x, card_y), (card_x + card_w, card_y + 45), (40, 110, 210), -1)
            
            # 红色圆形防伪印章 (官方售后保修直营章)
            stamp_cx = card_x + card_w - 75
            stamp_cy = card_y + card_h - 75
            cv2.circle(img, (stamp_cx, stamp_cy), 48, (40, 40, 220), 3)
            cv2.circle(img, (stamp_cx, stamp_cy), 42, (40, 40, 220), 1)
            # 五角星
            cv2.circle(img, (stamp_cx, stamp_cy), 6, (40, 40, 220), -1)

        # ── 4. 使用 PIL 渲染专业中文文字印章与卡片信息 ──
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        # 顶部左侧：电影级当前服务阶段提示条 (跟随滚轮变化)
        if t < 0.28:
            stage_text = "【第1幕】日常居家实态 · 空调运转故障智能诊断"
            stage_sub = "明亮居家客厅环境 · 检测到出风与传感器异常"
        elif t < 0.60:
            stage_text = "【第2幕】持证工程师上门 · 专业防尘垫与成套仪表就位"
            stage_sub = "15分钟极速响应 · 标准鞋套工具箱 · 全程透明录像"
        elif t < 0.82:
            stage_text = "【第3幕】规范拆检养护 · 高温深度除菌与原厂换件"
            stage_sub = "高压蒸汽消杀 · 抑菌滤网深层洁净 · 绝无乱收费"
        else:
            stage_text = "【第4幕】试机清爽如初 · 出具官方90天电子质保单"
            stage_sub = "平稳静音出风 · 官方全国联保 · 修不好立享退款"
            
        # 绘制半透明左上角阶段导视条
        draw.rectangle([(30, 25), (620, 92)], fill=(20, 30, 45, 210), outline=(230, 160, 40, 255), width=2)
        draw.text((45, 33), stage_text, font=font_sub, fill=(255, 215, 120))
        draw.text((45, 63), stage_sub, font=font_badge, fill=(225, 235, 245))
        
        # 如果是阶段 4，在质保卡上绘制专业字样
        if t >= 0.78:
            finish_phase = min(1.0, (t - 0.78) / 0.22)
            card_x = width - card_w - int(50 * finish_phase)
            card_y = int(height * 0.28)
            
            draw.text((card_x + 20, card_y + 10), "官方正品维修 90天全国联保凭证", font=font_badge, fill=(255, 255, 255))
            draw.text((card_x + 20, card_y + 60), "服务单号: WO-20261001-A90", font=font_badge, fill=(40, 50, 70))
            draw.text((card_x + 20, card_y + 90), "检修项目: 深度除菌养护 + 原厂精密调校", font=font_badge, fill=(40, 50, 70))
            draw.text((card_x + 20, card_y + 120), "工时配件: 明码标价 · 零隐形增项", font=font_badge, fill=(40, 50, 70))
            draw.text((card_x + 20, card_y + 150), "质保承诺: 90天内同故障免费二次上门", font=font_badge, fill=(210, 60, 20))
            draw.text((card_x + 20, card_y + 185), "施工技师: 金牌工程师 (持证认证编号: E-8821)", font=font_badge, fill=(90, 100, 115))
            
            # 印章文字
            draw.text((stamp_cx - 36, stamp_cy - 12), "官方质保", font=font_stamp, fill=(210, 40, 40))
            draw.text((stamp_cx - 28, stamp_cy + 14), "售后专用", font=font_badge, fill=(210, 40, 40))

        # 转回 OpenCV BGR 保存
        final_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        # 写入序列帧 (使用 pil_img.save 避免 Windows 中文路径导致 cv2.imwrite 失败)
        frame_filename = f"frame_{idx:03d}.jpg"
        frame_file_path = os.path.join(frames_dir, frame_filename)
        pil_img.save(frame_file_path, quality=92)
        video_out.write(final_frame)
        
        if idx % 30 == 0:
            print(f"进度: {idx}/{total_frames} 帧已完成...")

    video_out.release()
    print("序列帧与视频生成完毕！输出目录:", frames_dir)

if __name__ == '__main__':
    create_home_repair_movie()
