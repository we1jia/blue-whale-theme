"""生成蓝鲸主题的背景场景 hooks/scene.js（一个纯矢量 SVG 字符串）。

用法（在 mod 文件夹里执行；需要用户目录里的 numpy/opencv，所以不要加 -I）:
    python3 tools/build_scene.py

为什么是纯矢量：当前 App 版本 backdrop.image 不绘制，backdrop.scene 里嵌入的位图也会被拦掉，
只有矢量图形能显示。所以骑鲸少女和喷水鲸鱼用 tools/trace.py 从素材描摹成分层矢量路径。

为什么是静态：场景按整张图绘制，任何动画都会让 App 每帧重画整张图（含十万字符的人物路径），
持续占用 CPU，所以不加动画。

场景结构（根 svg 无 viewBox，铺满窗口）：
1. 底色渐变 + 柔光（居中 slice 层）
2. 底部多层波浪（贴底、横向拉伸）
3. 右侧：大弧形水面 + 骑鲸少女 + 气泡（右下对齐 meet 层，始终完整可见）
4. 左下：喷水鲸鱼 + 气泡（按 CSS 像素固定在侧栏底部，不随窗口缩放）
整段 SVG 必须 ≤ 131072 字符。
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from trace import to_group, trace  # noqa: E402

SRC = os.path.join(HERE, 'source', 'sprites.webp')
OUT = os.path.join(HERE, '..', 'hooks', 'scene.js')
OUT_DTS = os.path.join(HERE, '..', 'hooks', 'scene.d.ts')
LIMIT = 131072

sheet = Image.open(SRC).convert('RGBA')

# 骑鲸少女：从 x=900 裁；擦掉素材里波浪条/背景板的右边缘（x<925、y>245）。散落的气泡由描摹器丢弃
character = sheet.crop((900, 16, 1663, 936))
alpha = character.getchannel('A')
ImageDraw.Draw(alpha).rectangle((0, 245 - 16, 925 - 900, character.height), fill=0)
character.putalpha(alpha)
# 喷水鲸鱼（身体和水花是分开的几块，不能只留最大连通块）
whale = sheet.crop((81, 25, 394, 245))


def traced(im, height=None, width=None, **kw):
    if height:
        im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    if width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    layers, w, h = trace(np.array(im), **kw)
    return to_group(layers), w, h


def wave_path(baseline, amp, wavelength, x0=-200, x1=1800):
    """正弦波（q/t 半周期拼接），封底成填充形状；另返回顶边线用于白色高光"""
    half = wavelength / 2
    n = math.ceil((x1 - x0) / half)
    d = f'M{x0:.0f} {baseline:.1f} q{half / 2:.1f} {-amp * 2:.1f} {half:.1f} 0'
    d += f' t{half:.1f} 0' * (n - 1)
    end = x0 + half * n
    return d + f' L{end:.0f} 400 L{x0:.0f} 400 Z', d


# 波浪参数（坐标系 1600x400 的底部条带）：基线、振幅、波长、相位偏移、颜色、浓度
WAVES = [
    (155, 25, 1062, 0, '#cfdcfb', .47),
    (195, 34, 1312, -400, '#dccdf6', .33),
    (234, 29, 937, -150, '#bccff9', .51),
    (291, 26, 1156, -600, '#aec3f7', .59),
    (344, 17, 812, -300, '#c4d4fa', .47),
]


def bubble(cx, cy, r):
    """矢量玻璃气泡：透明芯、淡蓝边、左上高光"""
    hx, hy = cx - r * .35, cy - r * .4
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#bub)" stroke="#9fb4ff" stroke-opacity=".55" stroke-width="{max(.8, r / 14):.1f}"/>'
            f'<ellipse cx="{hx:.1f}" cy="{hy:.1f}" rx="{r * .32:.1f}" ry="{r * .2:.1f}" fill="#fff" fill-opacity=".85" transform="rotate(-35 {hx:.1f} {hy:.1f})"/>')


def build(char_cfg, whale_cfg):
    char_g, cw, chh = traced(character, height=char_cfg[0], k=char_cfg[1], eps=char_cfg[2], min_area=char_cfg[3])
    whale_g, ww, wh = traced(whale, width=whale_cfg[0], k=whale_cfg[1], eps=whale_cfg[2], min_area=4, keep_largest=False)

    defs = [
        '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3f1fd"/><stop offset="1" stop-color="#e5edfc"/></linearGradient>',
        '<radialGradient id="lav"><stop offset="0" stop-color="#efe2fb" stop-opacity=".8"/><stop offset="1" stop-color="#efe2fb" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="sky"><stop offset="0" stop-color="#dce8fd" stop-opacity=".85"/><stop offset="1" stop-color="#dce8fd" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="lit"><stop offset="0" stop-color="#ffffff" stop-opacity=".6"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="bub" cx=".5" cy=".5" r=".5"><stop offset=".6" stop-color="#ffffff" stop-opacity=".08"/><stop offset="1" stop-color="#b9caff" stop-opacity=".55"/></radialGradient>',
        '<filter id="soft" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="6"/></filter>',
    ]
    for i, (_, _, _, _, color, op) in enumerate(WAVES):
        defs.append(f'<linearGradient id="w{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity="{op * .55:.2f}"/><stop offset="1" stop-color="{color}" stop-opacity="{op:.2f}"/></linearGradient>')

    waves = []
    for i, (base, amp, wl, shift, _, _) in enumerate(WAVES):
        fill_d, rim_d = wave_path(base, amp, wl, x0=-200 + shift)
        waves.append(f'<path d="{fill_d}" fill="url(#w{i})"/>'
                     f'<path d="{rim_d}" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="1.6" vector-effect="non-scaling-stroke"/>')

    # 右侧层坐标（1600x1000，右下对齐）：由 2560x1584 合成稿 ×0.625 换算；少女占 x=1043、y=220、高 662
    side_wave = ('<path d="M781 1006 C1062 562 1219 162 1612 119 L1700 119 L1700 1006 Z" fill="#fff" fill-opacity=".36" filter="url(#soft)"/>'
                 '<path d="M781 1006 C1062 562 1219 162 1612 119" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="2"/>')
    s_char = 662 / chh
    right = ('<svg class="side" width="100%" height="100%" viewBox="0 0 1600 1000" preserveAspectRatio="xMaxYMax meet">' + side_wave
             + f'<g transform="translate(1043 220) scale({s_char:.4f})">{char_g}</g>'
             + bubble(1566, 209, 22) + bubble(1511, 139, 11) + bubble(1093, 362, 12.5) + bubble(1068, 406, 5.6)
             + bubble(1440, 560, 6) + bubble(1180, 600, 5) + '</svg>')
    # 侧栏宽度是固定像素：用原点在左下角（y=100%）、可溢出的嵌套 svg，按 CSS 像素定位鲸鱼（宽 126）
    s_whale = 126 / ww
    left = ('<svg x="0" y="100%" width="1" height="1" overflow="visible">'
            + f'<g transform="translate(14 -200) scale({s_whale:.4f})">{whale_g}</g>'
            + bubble(104, -214, 5) + bubble(119, -232, 3) + '</svg>')

    css = '@media (max-width:760px){.side{display:none}}'
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">'
            f'<defs>{"".join(defs)}</defs><style>{css}</style>'
            '<rect width="100%" height="100%" fill="url(#bg)"/>'
            '<svg width="100%" height="100%" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">'
            '<circle cx="75" cy="50" r="560" fill="url(#lav)"/><circle cx="1440" cy="440" r="625" fill="url(#sky)"/><circle cx="750" cy="125" r="500" fill="url(#lit)"/></svg>'
            f'<svg y="62%" width="100%" height="38%" viewBox="0 0 1600 400" preserveAspectRatio="none">{"".join(waves)}</svg>'
            f'{right}{left}</svg>')


# 从细到粗依次尝试，挑第一个不超预算的（少女：高、颜色数、化简误差、最小面积；鲸鱼：宽、颜色数、误差）
CANDIDATES = [
    ((560, 26, 1.2, 8), (240, 8, 1.1)),
    ((540, 24, 1.2, 8), (240, 8, 1.1)),
    ((520, 22, 1.2, 8), (240, 8, 1.1)),
    ((520, 20, 1.3, 9), (220, 8, 1.2)),
]
for char_cfg, whale_cfg in CANDIDATES:
    svg = build(char_cfg, whale_cfg)
    print(f'尝试 少女{char_cfg} 鲸鱼{whale_cfg}：{len(svg)} 字符')
    if len(svg) <= LIMIT - 512:
        break
else:
    raise SystemExit(f'场景超出 {LIMIT} 字符上限')

assert '`' not in svg and '${' not in svg and '\\' not in svg
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('// 由 tools/build_scene.py 生成，不要手改；改布局请改脚本后重新生成\n')
    f.write('export const SCENE = `' + svg + '`\n')
with open(OUT_DTS, 'w', encoding='utf-8') as f:
    f.write('// 由 tools/build_scene.py 生成\nexport declare const SCENE: string\n')
print(f'已生成 {os.path.normpath(OUT)}：{len(svg)} 字符（上限 {LIMIT}）')
