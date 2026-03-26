from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r'C:\Users\19044\.openclaw\workspace\scientific-ml-autoresearch')
out = root / 'promo' / 'xhs_cover.png'
out.parent.mkdir(parents=True, exist_ok=True)

W, H = 1242, 1660
bg = (8, 12, 18)
fg = (242, 246, 248)
muted = (134, 147, 158)
blue = (89, 220, 208)
blue_dark = (37, 78, 82)
yellow = (247, 197, 114)

img = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(img)

for y in range(0, H, 8):
    alpha = 8 + (y // 8) % 3
    d.line((0, y, W, y), fill=(10 + alpha, 14 + alpha, 20 + alpha))

for x in range(90, W - 90, 64):
    d.line((x, 110, x, H - 110), fill=(18, 26, 34), width=1)

# abstract evidence panels
panels = [
    (88, 120, 1154, 500),
    (88, 560, 1154, 980),
    (88, 1040, 1154, 1540),
]
for i, (x1, y1, x2, y2) in enumerate(panels):
    fill = (13 + i * 2, 20 + i * 4, 28 + i * 4)
    d.rounded_rectangle((x1, y1, x2, y2), radius=36, fill=fill, outline=(28, 40, 50), width=2)

# title block accent
for i in range(11):
    x1 = 120 + i * 48
    d.rounded_rectangle((x1, 618 + i * 4, x1 + 28, 780 - i * 6), radius=10, fill=blue if i in (2, 6, 9) else blue_dark)

# branch dots
branch_points = [(930, 680), (990, 710), (1050, 750), (960, 810), (1080, 840), (900, 880)]
for i, (x, y) in enumerate(branch_points):
    r = 13 if i in (1, 4) else 8
    d.ellipse((x-r, y-r, x+r, y+r), fill=yellow if i in (1, 4) else muted)

# lower bars
for i in range(7):
    y = 1120 + i * 42
    width = 180 + i * 95
    d.rounded_rectangle((120, y, 120 + width, y + 16), radius=6, fill=blue if i in (2, 5) else (46, 64, 72))

# fonts
font_candidates = [r'C:\Windows\Fonts\bahnschrift.ttf', r'C:\Windows\Fonts\segoeuib.ttf', r'C:\Windows\Fonts\arialbd.ttf']
font_path = next((p for p in font_candidates if Path(p).exists()), None)
if font_path:
    title_font = ImageFont.truetype(font_path, 92)
    mid_font = ImageFont.truetype(font_path, 44)
    body_font = ImageFont.truetype(font_path, 28)
    small_font = ImageFont.truetype(font_path, 22)
else:
    title_font = mid_font = body_font = small_font = ImageFont.load_default()

# text
d.text((120, 160), '一个面向 scientific ML 的', font=mid_font, fill=muted)
d.text((120, 235), 'AUTONOMOUS', font=title_font, fill=fg)
d.text((120, 340), 'RESEARCH WORKFLOW', font=title_font, fill=fg)
d.text((120, 470), '不是自动科学家，而是更克制的 research loop 工具', font=body_font, fill=blue)

d.text((120, 880), 'plan  /  run  /  summarize  /  suggest  /  repeat', font=body_font, fill=fg)
d.text((120, 1460), 'history-aware planning  ·  claim strength  ·  branch evidence', font=small_font, fill=muted)
d.text((120, 1500), 'constraints  ·  robustness hooks  ·  evaluation regimes', font=small_font, fill=muted)
d.text((120, 1550), 'github.com/chenyongssss/scientific-ml-autoresearch', font=small_font, fill=yellow)

img.save(out)
print(out)
