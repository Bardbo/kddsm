# 啃读点书吗？ 像素狗生成器 — 15 品种 × (奔跑6帧 / 跳跃 / 肖像)
# 16x16 网格 ×4 = 64px 帧；run 图集 384x64（6帧并排），jump 图集 128x64（2帧），idle 64x64
import os
from PIL import Image, ImageDraw

G = 16          # 逻辑网格
SCALE = 4
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons', 'dogs')
os.makedirs(OUT, exist_ok=True)

BLACK = (30, 30, 30)
WHITE = (252, 252, 252)

# ---------- 品种参数：毛色/腹色/耳型/眼色/斑点/尾型/腿长/体长/吻部色/鬃毛 ----------
BREEDS = {
  'dalmatian': dict(fur=WHITE, belly=(240,240,240), ear='point', ear_c=BLACK, eye='black', spots=BLACK, tail='up', legs='normal', body='normal', muzzle=WHITE, mane=False),
  'corgi':     dict(fur=(242,163,60),  belly=WHITE, ear='point', ear_c=(242,163,60), eye='black', spots=None, tail='up', legs='short', body='normal', muzzle=WHITE, mane=False),
  'shiba':     dict(fur=(232,130,43),  belly=(255,247,230), ear='point', ear_c=(232,130,43), eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(255,247,230), mane=False),
  'frenchy':   dict(fur=(198,138,91),  belly=(243,225,200), ear='bat', ear_c=(198,138,91), eye='black', spots=None, tail='up', legs='short', body='normal', muzzle=(243,225,200), mane=False),
  'bichon':    dict(fur=(253,253,253), belly=(240,240,240), ear='flop', ear_c=(253,253,253), eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(240,240,240), mane=True),
  'golden':    dict(fur=(232,182,76),  belly=(246,226,170), ear='flop', ear_c=(232,182,76), eye='black', spots=None, tail='up', legs='normal', body='normal', muzzle=(246,226,170), mane=False),
  'collie':    dict(fur=(58,58,68),    belly=WHITE, ear='point', ear_c=(58,58,68), eye='black', spots=None, tail='up', legs='normal', body='normal', muzzle=WHITE, mane=False),
  'samoyed':   dict(fur=WHITE, belly=(240,240,240), ear='point', ear_c=WHITE, eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(235,235,235), mane=False),
  'husky':     dict(fur=(183,188,196), belly=WHITE, ear='point', ear_c=(183,188,196), eye='blue', spots=None, tail='up', legs='normal', body='normal', muzzle=WHITE, mane=False),
  'dachshund': dict(fur=(139,90,43),   belly=(180,140,100), ear='flop', ear_c=(139,90,43), eye='black', spots=None, tail='straight', legs='short', body='long', muzzle=(180,140,100), mane=False),
  'schnauzer': dict(fur=(154,154,160), belly=(200,200,205), ear='flop', ear_c=(154,154,160), eye='black', spots=None, tail='straight', legs='normal', body='normal', muzzle=(200,200,205), mane=False),
  'akita':     dict(fur=(216,154,74),  belly=(246,226,170), ear='point', ear_c=(216,154,74), eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(246,226,170), mane=False),
  'tibetan':   dict(fur=(90,58,40),    belly=(130,95,70), ear='flop', ear_c=(90,58,40), eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(130,95,70), mane=True),
  'shepherd':  dict(fur=(46,42,36),    belly=(192,138,62), ear='point', ear_c=(46,42,36), eye='black', spots=None, tail='up', legs='normal', body='normal', muzzle=(192,138,62), mane=False),
  'poodle':    dict(fur=(232,230,227), belly=(210,208,205), ear='flop', ear_c=(232,230,227), eye='black', spots=None, tail='curl', legs='normal', body='normal', muzzle=(210,208,205), mane=True),
}

def px(d, x, y, c):
    d.point((x, y), fill=c)

def rect(d, x0, y0, x1, y1, c):
    d.rectangle([x0, y0, x1, y1], fill=c)

def dog_frame(img, b, frame, pose):
    """画一帧。侧身朝右。frame: 0-5 (run) / 0-1 (jump) / idle"""
    d = ImageDraw.Draw(img)
    body_top, body_h = 7, 6                      # 身体 y7..12
    leg_len = 3 if b['legs'] == 'short' else 4   # y12..14 / y12..15
    x_off = 0
    if pose == 'run':                            # 奔跑身体微沉/弹起
        x_off = [0, 1, 1, 0, -1, -1][frame]
        body_top = [7, 6, 6, 7, 8, 8][frame]
    elif pose == 'jump':                         # 跳跃：身体抬起、腿收起
        body_top = 4
    # 尾巴（身后）
    tail_c = b['fur']
    if pose == 'run':
        ty = [8, 6, 5, 6, 8, 9][frame]
        rect(d, 1, ty, 3, ty + 2, tail_c)
    elif pose == 'jump':
        rect(d, 1, 5, 3, 7, tail_c)
    else:  # idle
        rect(d, 1, 6, 3, 8, tail_c)
    if b['tail'] == 'curl':
        d.ellipse([0, 4, 3, 7], fill=tail_c)     # 卷尾

    # 鬃毛（比熊/藏獒/贵宾：身体更圆）
    mane_y = body_top - 1 if b['mane'] else body_top
    if b['mane']:
        rect(d, 3 + x_off, mane_y, 12 + x_off, body_top + body_h, b['fur'])

    # 身体
    rect(d, 3 + x_off, body_top, 12 + x_off, body_top + body_h, b['fur'])
    # 腹色带
    rect(d, 4 + x_off, body_top + body_h - 1, 11 + x_off, body_top + body_h, b['belly'])
    # 斑点（仅斑点狗）
    if b['spots']:
        rect(d, 5 + x_off, body_top + 1, 6 + x_off, body_top + 2, b['spots'])
        rect(d, 9 + x_off, body_top + 3, 10 + x_off, body_top + 4, b['spots'])

    # 腿（前/中/后）
    legs_x = [4 + x_off, 8 + x_off, 11 + x_off]
    leg_bottom = body_top + body_h + leg_len - 1
    if pose == 'run':
        # 交替步态：frame 偶奇，前腿后腿错开
        lift = {0: [0, 2, 0], 1: [1, 0, 1], 2: [2, 1, 2], 3: [0, 2, 0], 4: [1, 0, 1], 5: [2, 1, 2]}[frame]
        for i, lx in enumerate(legs_x):
            h = leg_len if lift[i] == 0 else leg_len - 1
            rect(d, lx, leg_bottom - h + 1, lx + 1, leg_bottom + (1 if lift[i] == 2 else 0), b['fur'])
    elif pose == 'jump':
        for lx in legs_x:                        # 收腿
            rect(d, lx, leg_bottom - 2, lx + 1, leg_bottom, b['fur'])
    else:
        for lx in legs_x:
            rect(d, lx, leg_bottom - leg_len + 1, lx + 1, leg_bottom, b['fur'])

    # 头（前上）
    hx = 10 + x_off
    if b['body'] == 'long':
        hx = 11 + x_off
    rect(d, hx, 4, hx + 5, 9, b['fur'])
    # 吻部
    rect(d, hx + 4, 6, hx + 6, 8, b['muzzle'])
    # 鼻头
    px(d, hx + 5, 7, BLACK)
    # 眼睛
    eye_c = (91, 141, 239) if b['eye'] == 'blue' else BLACK
    px(d, hx + 3, 5, eye_c)
    # 耳朵
    if b['ear'] == 'point':
        rect(d, hx, 1, hx + 2, 4, b['ear_c'])
        rect(d, hx + 3, 2, hx + 4, 4, b['ear_c'])
    elif b['ear'] == 'flop':
        rect(d, hx - 1, 2, hx + 2, 5, b['ear_c'])
    elif b['ear'] == 'bat':
        rect(d, hx, 1, hx + 1, 3, b['ear_c'])
        rect(d, hx + 3, 1, hx + 4, 3, b['ear_c'])
    # 额头斑纹：边牧/哈士奇白额，斑点狗黑耳斑
    if b.get('spots') and b['ear'] == 'point':
        px(d, hx + 2, 3, BLACK)

def sheet(name, frames, width):
    img = Image.new('RGBA', (width * G * SCALE, G * SCALE), (0, 0, 0, 0))
    for fi in range(frames):
        f = Image.new('RGBA', (G * SCALE, G * SCALE), (0, 0, 0, 0))
        small = Image.new('RGBA', (G, G), (0, 0, 0, 0))
        dog_frame(small, BREEDS[name], fi, 'run' if frames >= 5 else 'idle')
        f.paste(small.resize((G * SCALE, G * SCALE), Image.NEAREST), (0, 0))
        img.paste(f, (fi * G * SCALE, 0))
    img.save(os.path.join(OUT, f'{name}.png'))

for b in BREEDS:
    # run: 6 帧
    sheet(b, 6, 6)
    # jump: 2 帧（起跳+空中）
    img = Image.new('RGBA', (2 * G * SCALE, G * SCALE), (0, 0, 0, 0))
    for fi in range(2):
        f = Image.new('RGBA', (G, G), (0, 0, 0, 0))
        dog_frame(f, BREEDS[b], fi, 'jump')
        img.paste(f.resize((G * SCALE, G * SCALE), Image.NEAREST), (fi * G * SCALE, 0))
    img.save(os.path.join(OUT, f'{b}_jump.png'))
    # idle 肖像（正面对称：用 run 帧0 镜像不够好——直接复制 run 帧0 作为占位）
    img = Image.new('RGBA', (G * SCALE, G * SCALE), (0, 0, 0, 0))
    f = Image.new('RGBA', (G, G), (0, 0, 0, 0))
    dog_frame(f, BREEDS[b], 0, 'idle')
    img.paste(f.resize((G * SCALE, G * SCALE), Image.NEAREST), (0, 0))
    img.save(os.path.join(OUT, f'{b}_idle.png'))

print('generated:', len(os.listdir(OUT)), 'files in', OUT)
