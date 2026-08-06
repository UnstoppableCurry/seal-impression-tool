# 生成演示图：一张盖了红色公章的 A4 文档扫描件
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1240, 1754  # A4 @150dpi
FONT = "/Users/money/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/fonts/NotoSansSC-Regular.ttf"
FONT_B = "/Users/money/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/fonts/NotoSansSC-Bold.ttf"

# 纸面（微黄、带噪点）
img = np.full((H, W, 3), (243, 241, 235), np.uint8)  # BGR
noise = np.random.default_rng(7).integers(-6, 6, (H, W, 1))
img = np.clip(img.astype(int) + noise, 0, 255).astype(np.uint8)

pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(pil)
ft_title = ImageFont.truetype(FONT_B, 72)
ft_h = ImageFont.truetype(FONT_B, 40)
ft = ImageFont.truetype(FONT, 32)

d.text((W//2, 150), "委 托 检 测 协 议 书", font=ft_title, fill=(35, 35, 35), anchor="mm")
d.line((140, 230, W-140, 230), fill=(120, 120, 120), width=2)
lines = [
    "甲方（委托方）：某某生物科技有限公司",
    "乙方（检测方）：某某医学检验实验室",
    "",
    "一、甲方委托乙方对送检样本进行病理学检测，",
    "    检测项目包括组织切片染色与图像分析。",
    "二、样本数量：共计 24 例，以双方签字确认的",
    "    交接清单为准。",
    "三、检测周期：自样本接收之日起 15 个工作日。",
    "四、本协议一式两份，甲乙双方各执一份，",
    "    自盖章之日起生效。",
]
y = 300
for i, ln in enumerate(lines):
    d.text((160, y), ln, font=ft_h if i < 2 else ft, fill=(50, 50, 50))
    y += 78 if i < 2 else 58
d.text((W-520, H-420), "甲方盖章：", font=ft, fill=(50, 50, 50))
d.text((W-520, H-330), "日期：2026 年 8 月", font=ft, fill=(50, 50, 50))

# 红色公章：圆环 + 五角星 + 环形文字（盖在右下角签名区）
seal = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
s = ImageDraw.Draw(seal)
cx = cy = 260
s.ellipse((20, 20, 500, 500), outline=(200, 30, 30, 220), width=12)
# 五角星
pts = []
for i in range(10):
    r = 90 if i % 2 == 0 else 36
    a = -np.pi / 2 + i * np.pi / 5
    pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
s.polygon(pts, fill=(200, 30, 30, 220))
# 环形文字
ft_seal = ImageFont.truetype(FONT_B, 44)
text = "某某生物科技有限公司"
for i, ch in enumerate(text):
    a = -np.pi * 0.78 + i * (np.pi * 1.56) / (len(text) - 1)
    x, y2 = cx + 175 * np.cos(a), cy + 175 * np.sin(a)
    chimg = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    ImageDraw.Draw(chimg).text((30, 30), ch, font=ft_seal, fill=(200, 30, 30, 230), anchor="mm")
    chimg = chimg.rotate(-(a * 180 / np.pi + 90), resample=Image.BICUBIC, center=(30, 30))
    seal.alpha_composite(chimg, (int(x - 30), int(y2 - 30)))
# 印章做旧：随机磨损
mask = np.array(seal)[:, :, 3].astype(float)
wear = np.random.default_rng(3).random(mask.shape)
mask[wear < 0.18] *= 0.25
seal.putalpha(Image.fromarray(mask.astype(np.uint8)))
seal = seal.rotate(11, resample=Image.BICUBIC, expand=False)
pil = pil.convert("RGBA")
pil.alpha_composite(seal, (W - 640, H - 620))
pil = pil.convert("RGB")

out = "/Users/money/Documents/kimi/workspace/seal-impression-tool/docs/demo_document.png"
pil.save(out)
print("saved", out)
