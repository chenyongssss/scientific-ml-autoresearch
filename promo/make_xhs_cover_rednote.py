from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(r'C:\Users\19044\.openclaw\workspace\scientific-ml-autoresearch')
out = root / 'promo' / 'xhs_cover_rednote.png'
out.parent.mkdir(parents=True, exist_ok=True)

W, H = 1242, 1660
bg = (247, 245, 240)
panel = (255, 255, 255)
ink = (26, 28, 32)
muted = (103, 112, 122)
accent = (255, 84, 84)
accent_soft = (255, 228, 228)
line = (228, 224, 217)
blue = (74, 159, 166)

img = Image.new('RGB', (W, H), bg)
d = ImageDraw.Draw(img)

# soft background blocks
for y in range(0, H, 80):
    shade = 245 if (y // 80) % 2 == 0 else 242
    d.rectangle((0, y, W, y + 80), fill=(shade, shade - 2, shade - 6))

# main white card
card = (60, 70, W - 60, H - 70)
d.rounded_rectangle(card, radius=42, fill=panel, outline=line, width=2)

# top accent capsule
pill = (90, 105, 360, 165)
d.rounded_rectangle(pill, radius=28, fill=accent_soft)
d.text((118, 118), '开源项目 / AI4Science', fill=accent, font=ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc', 28) if Path(r'C:\Windows\Fonts\msyhbd.ttc').exists() else ImageFont.load_default())

# fonts
cn_bold = r'C:\Windows\Fonts\msyhbd.ttc'
cn_reg = r'C:\Windows\Fonts\msyh.ttc'
en_bold = r'C:\Windows\Fonts\bahnschrift.ttf'

if Path(cn_bold).exists():
    title_cn = ImageFont.truetype(cn_bold, 84)
    sub_cn = ImageFont.truetype(cn_bold, 44)
    body_cn = ImageFont.truetype(cn_reg if Path(cn_reg).exists() else cn_bold, 28)
    small_cn = ImageFont.truetype(cn_reg if Path(cn_reg).exists() else cn_bold, 22)
else:
    title_cn = sub_cn = body_cn = small_cn = ImageFont.load_default()
if Path(en_bold).exists():
    en_title = ImageFont.truetype(en_bold, 34)
    en_small = ImageFont.truetype(en_bold, 22)
else:
    en_title = en_small = ImageFont.load_default()

# main title
x = 100
d.text((x, 240), '我做了一个面向', font=sub_cn, fill=muted)
d.text((x, 320), 'SCIENTIFIC ML 的', font=en_title, fill=blue)
d.text((x, 390), '研究工作流工具', font=title_cn, fill=ink)

# emphasis block
highlight = (100, 560, 1060, 760)
d.rounded_rectangle(highlight, radius=30, fill=(250, 248, 244), outline=line, width=2)
d.text((130, 600), '不是“自动科学家”', font=sub_cn, fill=ink)
d.text((130, 662), '而是更克制的', font=body_cn, fill=muted)
d.text((360, 650), 'plan / run / summarize / suggest', font=en_title, fill=accent)

# benefits list blocks
items = [
    ('history-aware planning', '会根据历史结果规划下一轮'),
    ('claim strength', '避免把局部结果过早包装成结论'),
    ('constraints / robustness', '把 scientific checks 显式写进 workflow'),
]
start_y = 850
for i, (a, b) in enumerate(items):
    y = start_y + i * 165
    d.rounded_rectangle((100, y, 1060, y + 120), radius=24, fill=(252, 252, 252), outline=line, width=2)
    d.rounded_rectangle((122, y + 28, 154, y + 60), radius=10, fill=accent if i == 0 else blue if i == 1 else (255, 187, 92))
    d.text((176, y + 18), a, font=en_title, fill=ink)
    d.text((176, y + 64), b, font=body_cn, fill=muted)

# footer
footer_y = 1450
d.line((100, footer_y, 1060, footer_y), fill=line, width=2)
d.text((100, 1492), 'scientific-ml-autoresearch', font=en_title, fill=ink)
d.text((100, 1542), 'github.com/chenyongssss/scientific-ml-autoresearch', font=en_small, fill=muted)
d.text((890, 1498), '适合发封面', font=small_cn, fill=accent)

img.save(out)
print(out)
