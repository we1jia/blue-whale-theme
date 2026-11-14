"""合成蓝鲸主题的整张背景图（只用 PIL，无 numpy）。

用法（在 mod 文件夹里执行）:
    python3 -I tools/compose_backdrop.py tools/source/sprites.webp assets/backdrop-v2.jpg
素材：tools/source/sprites.webp 是用户提供的透明底切图（鲸鱼、气泡、波浪、骑鲸少女），
tools/source/reference-mockup.webp 是用户给的效果参考图，只用来对照布局。
画布 2560x1584，对应约 1.62 的窗口比例（与用户截图一致）。
布局参照用户给的效果图：左下侧栏位置放喷水鲸鱼，右侧放骑鲸少女，底部多层半透明波浪。
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]
W, H = 2560, 1584
SS = 2  # 波浪超采样倍数，抗锯齿

asset = Image.open(SRC).convert('RGBA')


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vertical_gradient(w, h, top, bottom):
    """上下两色的竖向渐变"""
    mask = Image.linear_gradient('L').resize((w, h))
    return Image.composite(Image.new('RGB', (w, h), hex_rgb(bottom)), Image.new('RGB', (w, h), hex_rgb(top)), mask)


def soft_blob(canvas, center, radius, color, strength):
    """在画布上叠一团柔和的径向光"""
    g = Image.radial_gradient('L').resize((radius * 2, radius * 2))  # 中心 0，内切圆边缘约 181，角上 255
    # 在内切圆边缘（181）处衰减到 0，平方曲线让过渡更柔，避免方形硬边
    mask = g.point(lambda v: int(255 * strength * max(0.0, 1 - v / 181) ** 2))
    layer = Image.new('RGBA', (radius * 2, radius * 2), hex_rgb(color) + (0,))
    layer.putalpha(mask)
    canvas.alpha_composite(layer, (center[0] - radius, center[1] - radius))


def wave_points(baseline, amp, wavelength, phase, amp2=0.0, wl2=1.0, ph2=0.0):
    """返回一条波浪的折线点（超采样坐标），两组正弦叠加更自然"""
    pts = []
    for x in range(-20, W * SS + 21, 6):
        xs = x / SS
        y = baseline + amp * math.sin(2 * math.pi * xs / wavelength + phase)
        y += amp2 * math.sin(2 * math.pi * xs / wl2 + ph2)
        pts.append((x, y * SS))
    return pts


def draw_wave(canvas, baseline, amp, wavelength, phase, color, alpha, rim_alpha, amp2=0.0, wl2=1.0, ph2=0.0):
    """画一层半透明波浪：内部自上而下变浓，顶边一道白色高光"""
    pts = wave_points(baseline, amp, wavelength, phase, amp2, wl2, ph2)
    big = (W * SS, H * SS)
    # 填充遮罩
    mask = Image.new('L', big, 0)
    ImageDraw.Draw(mask).polygon(pts + [(W * SS + 20, H * SS), (-20, H * SS)], fill=255)
    # 竖向透明度渐变：波顶淡、往下浓
    top_y = int((baseline - amp - amp2) * SS)
    grad = Image.new('L', big, 0)
    gpart = Image.linear_gradient('L').resize((big[0], max(1, big[1] - top_y)))
    gpart = gpart.point(lambda v: int(alpha * (0.55 + 0.45 * v / 255)))
    grad.paste(gpart, (0, top_y))
    from PIL import ImageChops
    fill_mask = ImageChops.multiply(mask, grad)
    layer = Image.new('RGBA', big, hex_rgb(color) + (0,))
    layer.putalpha(fill_mask)
    # 顶边高光
    rim = Image.new('L', big, 0)
    ImageDraw.Draw(rim).line(pts, fill=rim_alpha, width=3 * SS, joint='curve')
    rim = rim.filter(ImageFilter.GaussianBlur(1.2 * SS))
    rim_layer = Image.new('RGBA', big, (255, 255, 255, 0))
    rim_layer.putalpha(rim)
    layer.alpha_composite(rim_layer)
    layer = layer.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    canvas.alpha_composite(layer)


def big_side_wave(canvas):
    """右侧一道从底部升到右上角的大弧形浅色水面，参照效果图右上的大波"""
    big = (W * SS, H * SS)
    pts = []
    # 三次贝塞尔：从底部中右侧升到右上角
    p0, p1, p2, p3 = (1250, H + 10), (1700, 900), (1950, 260), (W + 20, 190)
    for i in range(0, 201):
        t = i / 200
        x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
        pts.append((x * SS, y * SS))
    mask = Image.new('L', big, 0)
    ImageDraw.Draw(mask).polygon(pts + [(W * SS + 40, H * SS + 40)], fill=95)
    mask = mask.filter(ImageFilter.GaussianBlur(10 * SS))
    layer = Image.new('RGBA', big, (255, 255, 255, 0))
    layer.putalpha(mask)
    rim = Image.new('L', big, 0)
    ImageDraw.Draw(rim).line(pts, fill=110, width=3 * SS, joint='curve')
    rim = rim.filter(ImageFilter.GaussianBlur(2.5 * SS))
    rl = Image.new('RGBA', big, (255, 255, 255, 0))
    rl.putalpha(rim)
    layer.alpha_composite(rl)
    canvas.alpha_composite(layer.resize((W, H), Image.LANCZOS))


def paste_asset(canvas, box, height=None, width=None, at=(0, 0), opacity=1.0):
    """从素材图裁一块，按高或宽等比缩放后贴到画布"""
    piece = asset.crop(box)
    if height:
        piece = piece.resize((round(piece.width * height / piece.height), height), Image.LANCZOS)
    elif width:
        piece = piece.resize((width, round(piece.height * width / piece.width)), Image.LANCZOS)
    if opacity < 1:
        a = piece.getchannel('A').point(lambda v: int(v * opacity))
        piece.putalpha(a)
    canvas.alpha_composite(piece, at)
    return piece.size


# 1. 底色：上方略带薰衣草，下方偏海蓝
canvas = vertical_gradient(W, H, '#f3f1fd', '#e5edfc').convert('RGBA')
soft_blob(canvas, (120, 80), 900, '#efe2fb', 0.75)   # 左上淡紫粉
soft_blob(canvas, (2300, 700), 1000, '#dce8fd', 0.8)  # 右侧淡蓝
soft_blob(canvas, (1200, 200), 800, '#ffffff', 0.55)  # 中上提亮，保证正文区干净

# 2. 右侧大弧形水面
big_side_wave(canvas)

# 3. 底部多层波浪（从后往前）
draw_wave(canvas, 1215, 38, 1700, 0.3, '#cfdcfb', 120, 150, amp2=14, wl2=640, ph2=1.0)
draw_wave(canvas, 1275, 52, 2100, 1.9, '#dccdf6', 85, 130, amp2=12, wl2=760, ph2=2.2)
draw_wave(canvas, 1335, 44, 1500, 3.1, '#bccff9', 130, 160, amp2=10, wl2=520, ph2=0.4)
draw_wave(canvas, 1420, 40, 1850, 0.9, '#aec3f7', 150, 175, amp2=9, wl2=600, ph2=1.7)
draw_wave(canvas, 1500, 26, 1300, 2.4, '#c4d4fa', 120, 140)

# 4. 左下：喷水鲸鱼，按用户要求放回侧栏底部（与效果图一致）
paste_asset(canvas, (81, 25, 394, 245), width=300, at=(64, 1012))

# 5. 右侧：骑鲸少女，底边落在约 1412，与效果图一致
# 裁剪左边界从 900 开始，把角色左侧的气泡完整带上；
# 但素材里波浪条和背景板的右边缘在 x<925、y>245 处，要擦掉，否则会出现一道竖线
crop_box = (900, 16, 1663, 936)
piece = asset.crop(crop_box)
alpha = piece.getchannel('A')
ImageDraw.Draw(alpha).rectangle((0, 245 - crop_box[1], 925 - crop_box[0], piece.height), fill=0)
piece.putalpha(alpha)
piece_h = 1060
piece = piece.resize((round(piece.width * piece_h / piece.height), piece_h), Image.LANCZOS)
canvas.alpha_composite(piece, (W - piece.width - 12, 1412 - piece_h))

# 6. 点缀气泡：用素材里的大气泡缩放
bubble = (758, 101, 888, 229)
for (x, y, s, o) in [(2470, 300, 70, 0.9), (2400, 205, 34, 0.85), (1730, 560, 40, 0.8), (1700, 640, 18, 0.75),
                     (330, 960, 22, 0.8), (372, 920, 13, 0.75), (1000, 1180, 26, 0.55), (1500, 1120, 20, 0.5)]:
    paste_asset(canvas, bubble, width=s, at=(x, y), opacity=o)

# 必须是基线 JPEG：渐进式 JPEG 在 App 里读不出来，会静默退回默认背景
canvas.convert('RGB').save(OUT, 'JPEG', quality=88, optimize=True, progressive=False, subsampling='4:2:0')
print('saved', OUT)
