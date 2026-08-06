# 自动演示并截取软件各阶段界面截图
import os, sys, time, subprocess
import tkinter as tk
import numpy as np
import cv2
import Quartz

BASE = "/Users/money/Documents/kimi/workspace/seal-impression-tool"
SHOTS = os.path.join(BASE, "docs", "screenshots")
sys.path.insert(0, BASE)
from main import SimpleImageThresholdTool

root = tk.Tk()
tool = SimpleImageThresholdTool(root)
root.update()

def my_window_id():
    pid = os.getpid()
    opts = Quartz.kCGWindowListOptionOnScreenOnly
    wins = Quartz.CGWindowListCopyWindowInfo(opts, Quartz.kCGNullWindowID)
    cands = [w for w in wins
             if w.get(Quartz.kCGWindowOwnerPID) == pid
             and w.get(Quartz.kCGWindowLayer, -1) == 0
             and w.get(Quartz.kCGWindowBounds, {}).get('Width', 0) > 400]
    cands.sort(key=lambda w: w[Quartz.kCGWindowBounds]['Width'] * w[Quartz.kCGWindowBounds]['Height'], reverse=True)
    return cands[0][Quartz.kCGWindowNumber] if cands else None

def shot(name):
    root.update_idletasks(); root.update()
    time.sleep(0.9)
    root.update()
    wid = my_window_id()
    out = os.path.join(SHOTS, name)
    if wid:
        subprocess.run(["screencapture", "-x", "-o", "-l", str(wid), out], check=True)
        print("shot:", name, "wid", wid)
    else:
        print("NO WINDOW for", name)

# --- 阶段 1：初始界面 ---
shot("01_welcome.png")

# --- 阶段 2：加载演示图 ---
img = cv2.imread(os.path.join(BASE, "docs", "demo_document.png"))
tool.original_image = img
tool.gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
tool.zoom_level = 1.0
tool.pan_x = tool.pan_y = 0
tool.lasso_used = False
tool.enable_global_controls()
tool.update_global_threshold()
h, w = img.shape[:2]
tool.status_label.config(text=f"Image loaded: {w}x{h}, converted to grayscale")
tool.fit_to_window()
shot("02_loaded_default.png")

# --- 阶段 3：调整全局阈值（红色印章在灰度图里偏暗，保留 30~150）---
tool.global_threshold_min.set(30)
tool.global_threshold_max.set(150)
tool.update_global_threshold()
shot("03_global_threshold.png")

# --- 阶段 4：套索圈选印章区域 + 局部阈值预览 ---
tool.start_selection()
zl = tool.zoom_level
cx, cy, r = 860, 1394, 300  # 印章在图中的位置
pts = []
for a in np.linspace(0, 2 * np.pi, 28, endpoint=False):
    pts.append(((cx + r * np.cos(a)) * zl, (cy + r * np.sin(a)) * zl))
tool.lasso_points = pts
for i in range(1, len(pts)):
    tool.canvas.create_line(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1], fill="red", width=2, tags="lasso")
tool.create_selection_mask()
tool.local_threshold_min.set(40)
tool.local_threshold_max.set(140)
tool.display_binary_image_with_preview()
shot("04_lasso_preview.png")

# --- 阶段 5：应用局部阈值 ---
tool.apply_local_threshold()
shot("05_applied.png")

# --- 阶段 6：纯黑白显示模式 ---
tool.visual_mode.set("纯二值")
tool.update_display()
shot("06_bw_mode.png")

# --- 附带：导出的红白效果图（README 展示用）---
h, w = tool.binary_image.shape
red_white = np.zeros((h, w, 3), np.uint8)
red_white[tool.binary_image == 255] = [0, 0, 255]
red_white[tool.binary_image == 0] = [255, 255, 255]
cv2.imwrite(os.path.join(SHOTS, "07_export_result.png"), red_white)
print("exported demo result")

root.destroy()
print("done")
