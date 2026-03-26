from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r'C:\Users\19044\.openclaw\workspace\scientific-ml-autoresearch')
out_dir = root / 'promo'
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / 'xhs_poster.png'

W, H = 1242, 1660
bg = (10, 14, 18)
fg = (232, 238, 242)
muted = (120, 138, 152)
blue = (92, 214, 203)
blue2 = (58, 120, 122)
accent = (244, 191, 117)

img = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(img)

for x in range(90, W - 90, 48):
    d.line((x, 120, x, H - 120), fill=(20, 28, 34), width=1)
for y in range(120, H - 120, 48):
    d.line((90, y, W - 90, y), fill=(18, 24, 30), width=1)

rail_x = 120
for i in range(18):
    y = 180 + i * 68
    color = blue if i in (3, 7, 12, 15) else blue2
    d.rounded_rectangle((rail_x, y, rail_x + 16, y + 36), radius=6, fill=color)
    if i < 17:
        d.line((rail_x + 8, y + 36, rail_x + 8, y + 68), fill=(45, 70, 72), width=2)

blocks = [
    (250, 250, 980, 510, (18, 28, 34)),
    (250, 560, 980, 820, (14, 24, 30)),
    (250, 870, 980, 1130, (18, 30, 36)),
]
for x1, y1, x2, y2, c in blocks:
    d.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=c, outline=(34, 50, 56), width=2)

for idx, (x1, y1, x2, y2, c) in enumerate(blocks):
    base_y = y1 + 52
    for j in range(8):
        bw = 90 + j * 44 if idx == 0 else 120 + j * 36 if idx == 1 else 80 + j * 52
        col = blue if ((j == 5 and idx != 2) or (j == 6 and idx == 2)) else (52, 74, 78)
        d.rounded_rectangle((x1 + 36, base_y + j * 20, x1 + 36 + bw, base_y + j * 20 + 10), radius=4, fill=col)

for i in range(6):
    x = 910 + i * 28
    d.line((x, 160, x, 210), fill=(40, 60, 68), width=2)
    d.ellipse((x - 4, 150, x + 4, 158), fill=accent if i in (1, 4) else muted)

dot_positions = [(1030, 610), (1080, 650), (990, 700), (1060, 740), (1010, 790)]
for i, (x, y) in enumerate(dot_positions):
    r = 10 if i in (1, 3) else 7
    d.ellipse((x - r, y - r, x + r, y + r), fill=blue if i in (1, 3) else muted)

d.line((90, 1390, W - 90, 1390), fill=(38, 56, 64), width=2)

font_paths = [
    r'C:\Windows\Fonts\bahnschrift.ttf',
    r'C:\Windows\Fonts\segoeui.ttf',
    r'C:\Windows\Fonts\arial.ttf',
]
font_path = next((p for p in font_paths if Path(p).exists()), None)
if font_path:
    title_font = ImageFont.truetype(font_path, 88)
    subtitle_font = ImageFont.truetype(font_path, 28)
    body_font = ImageFont.truetype(font_path, 34)
    small_font = ImageFont.truetype(font_path, 22)
else:
    title_font = subtitle_font = body_font = small_font = ImageFont.load_default()

d.text((250, 110), 'scientific-ml', font=subtitle_font, fill=muted)
d.text((250, 150), 'AUTORESEARCH', font=title_font, fill=fg)
d.text((255, 1260), 'A minimal autonomous research workflow for scientific machine learning', font=body_font, fill=fg)
d.text((250, 1318), 'plan / run / summarize / suggest / repeat', font=subtitle_font, fill=blue)
d.text((250, 1450), 'history-aware planning  ·  evidence tracking  ·  claim strength', font=small_font, fill=muted)
d.text((250, 1490), 'constraints  ·  robustness hooks  ·  evaluation regimes', font=small_font, fill=muted)
d.text((250, 1540), 'github.com/chenyongssss/scientific-ml-autoresearch', font=small_font, fill=accent)

labels = [
    ('ROUND MODE', 278, 276),
    ('CLAIM TRAJECTORY', 278, 586),
    ('BRANCH EVIDENCE', 278, 896),
]
for t, x, y in labels:
    d.text((x, y), t, font=small_font, fill=muted)

img.save(out)
print(out)
