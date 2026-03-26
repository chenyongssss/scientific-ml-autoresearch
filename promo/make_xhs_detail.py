from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r'C:\Users\19044\.openclaw\workspace\scientific-ml-autoresearch')
out = root / 'promo' / 'xhs_detail.png'
out.parent.mkdir(parents=True, exist_ok=True)

W, H = 1242, 1660
bg = (246, 248, 250)
fg = (20, 26, 32)
muted = (96, 108, 120)
blue = (49, 154, 151)
dark = (18, 30, 40)
line = (220, 226, 232)

img = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(img)

for y in range(120, H - 100, 64):
    d.line((80, y, W - 80, y), fill=line, width=1)

cards = [
    (80, 170, 1162, 410),
    (80, 460, 1162, 760),
    (80, 810, 1162, 1120),
    (80, 1170, 1162, 1510),
]
for x1, y1, x2, y2 in cards:
    d.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=(255, 255, 255), outline=line, width=2)

font_candidates = [r'C:\Windows\Fonts\bahnschrift.ttf', r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\arial.ttf']
font_path = next((p for p in font_candidates if Path(p).exists()), None)
if font_path:
    title_font = ImageFont.truetype(font_path, 64)
    h_font = ImageFont.truetype(font_path, 34)
    body_font = ImageFont.truetype(font_path, 28)
    small_font = ImageFont.truetype(font_path, 22)
else:
    title_font = h_font = body_font = small_font = ImageFont.load_default()

# title
d.text((80, 60), '这个项目现在能做什么？', font=title_font, fill=dark)

# card 1
d.text((120, 205), '01  Workflow', font=h_font, fill=blue)
d.text((120, 265), 'plan  →  run  →  summarize  →  suggest  →  loop', font=body_font, fill=fg)
d.text((120, 315), '把 scientific ML 里最常见的实验闭环整理成一个轻量 CLI workflow。', font=body_font, fill=muted)

# card 2
d.text((120, 500), '02  Research control', font=h_font, fill=blue)
d.text((120, 560), 'explore / exploit / ablate / validate / stop', font=body_font, fill=fg)
d.text((120, 610), '不只是跑实验，也开始编码“下一轮应该怎么走”的研究动作。', font=body_font, fill=muted)
d.text((120, 660), '支持 history-aware planning、early stop、status / summary / suggestion。', font=body_font, fill=muted)

# card 3
d.text((120, 850), '03  Scientific ML-aware checks', font=h_font, fill=blue)
d.text((120, 910), 'constraints / robustness hooks / evaluation regimes', font=body_font, fill=fg)
d.text((120, 960), '把 scientific constraints 和验证需求显式写进 task，而不是只放在脑子里。', font=body_font, fill=muted)
d.text((120, 1010), '更适合 PDE learning、operator learning、inverse problems 等方向。', font=body_font, fill=muted)

# card 4
d.text((120, 1210), '04  Evidence-aware reporting', font=h_font, fill=blue)
d.text((120, 1270), 'claim strength / claim trajectory / branch evidence', font=body_font, fill=fg)
d.text((120, 1320), '区分 observed、needs-validation、supported、uncertain。', font=body_font, fill=muted)
d.text((120, 1370), '尽量避免把局部结果过早包装成“已经成立的结论”。', font=body_font, fill=muted)
d.text((120, 1460), 'GitHub: chenyongssss/scientific-ml-autoresearch', font=small_font, fill=dark)

img.save(out)
print(out)
