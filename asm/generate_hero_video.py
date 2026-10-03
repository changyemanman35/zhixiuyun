import os
import cv2
import numpy as np
import math

def create_hero_video():
    width = 1280
    height = 720
    fps = 30
    duration_sec = 6
    total_frames = fps * duration_sec
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'videos', 'hardware_teardown.mp4')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (width, height))

    print(f"正在渲染硬件解构电影级视频 (共 {total_frames} 帧)...")

    cx, cy = width // 2, height // 2

    for frame_idx in range(total_frames):
        t = frame_idx / total_frames  # 0.0 -> 1.0

        # 1. 电影级深空蓝紫底色
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 渐变底色
        bg_blue = int(18 + 12 * math.sin(t * math.pi))
        bg_green = int(10 + 6 * math.cos(t * math.pi))
        frame[:, :] = (bg_blue, bg_green, 6)

        # 2. 绘制电路网底纹 (PCB 网格微光)
        grid_step = 60
        for x in range(0, width, grid_step):
            cv2.line(frame, (x, 0), (x, height), (35, 25, 12), 1)
        for y in range(0, height, grid_step):
            cv2.line(frame, (0, y), (width, y), (35, 25, 12), 1)

        # 3. 随时间推移的机械解构与微观潜入 (三种阶段模拟章鱼掀开水面潜入深海)
        # 阶段 A (0~0.35): 整机外观与金属高光
        # 阶段 B (0.35~0.7): 外壳 3D 分离爆开，散热器与激光线
        # 阶段 C (0.7~1.0): 镜头深潜入主板芯片中心，电流激荡

        teardown_progress = max(0.0, min(1.0, (t - 0.25) / 0.5))  # 机械掀开分离进度
        zoom = 1.0 + 0.8 * (t ** 1.5)  # 镜头推入缩放

        # 绘制主板电路脉冲线 (随着镜头流动)
        pulse_offset = int(frame_idx * 16)
        line_color = (255, 200, 22) if t > 0.5 else (220, 140, 20)
        
        # 几条主总线
        pts1 = np.array([[100, cy], [cx - 200, cy], [cx - 100, cy - 80], [cx + 100, cy - 80], [cx + 200, cy], [width - 100, cy]], np.int32)
        cv2.polylines(frame, [pts1], False, (140, 80, 20), 2, cv2.LINE_AA)
        
        pts2 = np.array([[200, cy + 120], [cx - 150, cy + 120], [cx, cy + 40], [cx + 150, cy + 120], [width - 200, cy + 120]], np.int32)
        cv2.polylines(frame, [pts2], False, (160, 100, 30), 2, cv2.LINE_AA)

        # 脉冲流动光斑
        dot1_x = int((frame_idx * 14) % width)
        dot1_y = cy if dot1_x < cx - 100 else (cy - 80 if dot1_x < cx + 100 else cy)
        cv2.circle(frame, (dot1_x, dot1_y), 6, (255, 255, 120), -1)
        cv2.circle(frame, (dot1_x, dot1_y), 14, (255, 200, 50), 2)

        # 4. 绘制核心硬件单元 (机身外壳与芯片)
        shell_offset = int(teardown_progress * 180)  # 外壳向左右分离距离 (对应掀开水面)

        # 左外壳 (向左分离)
        left_shell_x1 = int(cx - 220 * zoom - shell_offset)
        left_shell_x2 = int(cx - 10 * zoom - shell_offset)
        left_shell_y1 = int(cy - 140 * zoom)
        left_shell_y2 = int(cy + 140 * zoom)
        if left_shell_x1 < left_shell_x2:
            cv2.rectangle(frame, (left_shell_x1, left_shell_y1), (left_shell_x2, left_shell_y2), (70, 50, 25), -1)
            cv2.rectangle(frame, (left_shell_x1, left_shell_y1), (left_shell_x2, left_shell_y2), (180, 120, 40), 2)

        # 右外壳 (向右分离)
        right_shell_x1 = int(cx + 10 * zoom + shell_offset)
        right_shell_x2 = int(cx + 220 * zoom + shell_offset)
        right_shell_y1 = int(cy - 140 * zoom)
        right_shell_y2 = int(cy + 140 * zoom)
        if right_shell_x1 < right_shell_x2:
            cv2.rectangle(frame, (right_shell_x1, right_shell_y1), (right_shell_x2, right_shell_y2), (70, 50, 25), -1)
            cv2.rectangle(frame, (right_shell_x1, right_shell_y1), (right_shell_x2, right_shell_y2), (180, 120, 40), 2)

        # 5. 内部微观核心主板与芯片 (被掀开后展露出来，随缩放逐渐放大占满镜头)
        core_w = int(160 * zoom)
        core_h = int(160 * zoom)
        core_x1, core_y1 = cx - core_w // 2, cy - core_h // 2
        core_x2, core_y2 = cx + core_w // 2, cy + core_h // 2

        # 纯铜散热模组与芯片底座
        cv2.rectangle(frame, (core_x1 - 20, core_y1 - 20), (core_x2 + 20, core_y2 + 20), (30, 80, 180), -1)  # 铜色
        cv2.rectangle(frame, (core_x1, core_y1), (core_x2, core_y2), (25, 20, 15), -1)  # 黑色硅芯片

        # 芯片引脚与金属发光触点
        pin_spacing = int(14 * zoom)
        for px in range(core_x1, core_x2, max(8, pin_spacing)):
            cv2.line(frame, (px, core_y1 - 12), (px, core_y1), (220, 200, 100), 2)
            cv2.line(frame, (px, core_y2), (px, core_y2 + 12), (220, 200, 100), 2)

        # 芯片核心发光文字与徽章
        chip_glow = int(160 + 90 * math.sin(t * 8 * math.pi))
        cv2.rectangle(frame, (core_x1 + 15, core_y1 + 15), (core_x2 - 15, core_y2 - 15), (chip_glow, int(chip_glow * 0.8), 20), 2)

        # 激光全息扫描线 (自上而下扫过)
        laser_y = int(cy - 160 * zoom + ((frame_idx * 12) % int(320 * zoom)))
        cv2.line(frame, (cx - int(240 * zoom), laser_y), (cx + int(240 * zoom), laser_y), (80, 255, 80), 2, cv2.LINE_AA)
        cv2.line(frame, (cx - int(240 * zoom), laser_y), (cx + int(240 * zoom), laser_y), (150, 255, 180), 1, cv2.LINE_AA)

        # 科技文字标注
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "ASM OFFICIAL SERVICE - HARDWARE TEARDOWN", (40, 50), font, 0.7, (200, 200, 200), 2, cv2.LINE_AA)
        cv2.putText(frame, f"CORE FREQ: 4.8GHz  |  SLA: 99.98%  |  FRAME: {frame_idx:03d}", (40, 80), font, 0.5, (100, 220, 100), 1, cv2.LINE_AA)

        # 底部滚动指示
        if t < 0.6:
            cv2.putText(frame, "SCROLL TO EXPLORE TEARDOWN v", (cx - 180, height - 40), font, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "DEEP SILICON CORE INSPECTION", (cx - 170, height - 40), font, 0.65, (100, 240, 255), 2, cv2.LINE_AA)

        out.write(frame)

    out.release()
    file_size = os.path.getsize(output_path)
    print(f"渲染完成！视频文件保存至: {output_path} (大小: {file_size / 1024:.1f} KB)")

if __name__ == '__main__':
    create_hero_video()
