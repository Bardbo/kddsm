# 重染 CC0 奔跑动画 → 各品种毛色（保留骨架动画，替换主毛色）
# 源：white/black/brown/shepherd 四套动画（run 6帧/jump 6帧/idle）
# 品种映射：brown 系按 HSV 色相重染（柯基黄褐/柴犬橙/金毛金/法斗奶油/雪纳瑞灰/罗威纳黑棕），白/黑系复制
import os, colorsys
from PIL import Image
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'icons', 'dogs')

# 品种 → (源动画, 目标毛色 RGB 或 None=原样)
MAP = {
    'dalmatian': ('white', None), 'samoyed': ('white', None), 'bichon': ('white', None), 'poodle': ('white', None),
    'collie': ('black', None), 'tibetan': ('black', None),
    'husky': ('black', (150, 158, 172)),          # 灰蓝
    'shepherd': ('shepherd', None),
    'dachshund': ('brown', None),                  # 深棕原样
    'corgi': ('brown', (200, 155, 74)),            # 柯基黄褐
    'shiba': ('brown', (217, 122, 43)),            # 柴犬橙
    'golden': ('brown', (224, 169, 60)),           # 金毛金
    'frenchy': ('brown', (232, 205, 168)),         # 法斗奶油
    'schnauzer': ('brown', (154, 154, 154)),       # 雪纳瑞灰
    'rottweiler': ('brown', (92, 58, 36)),         # 罗威纳黑棕
}

def hsv_sub(img, target):
    """把主毛色（棕橙带，H 10-50°）像素的色相/亮度映射到目标色，保留黑白像素"""
    a = np.array(img.convert('RGBA')).astype(np.float32) / 255.0
    th = np.zeros(a.shape[:2], dtype=bool)
    out = a.copy()
    tr, tg, tb = target[0] / 255.0, target[1] / 255.0, target[2] / 255.0
    th_r, th_g, th_b = colorsys.rgb_to_hsv(tr, tg, tb)
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            r, g, b, al = a[y, x]
            if al < 0.1: continue
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            if 0.08 <= h <= 0.16 and s > 0.10 and v > 0.25:      # 棕橙带
                nr, ng, nb = colorsys.hsv_to_rgb(th_r, s * 0.85, v * (0.75 + 0.35 * (th_g > th_r)))  # 保留明度轮廓
                out[y, x] = (nr, ng, nb, al)
    return Image.fromarray((out * 255).astype(np.uint8), 'RGBA')

for breed, (src, target) in MAP.items():
    for kind in ('run', 'jump', 'idle'):
        sp = os.path.join(SRC, f'{src}_{kind}.png')
        if not os.path.exists(sp):
            print('missing src:', sp); continue
        im = Image.open(sp).convert('RGBA')
        out = hsv_sub(im, target) if target else im
        out.save(os.path.join(SRC, f'{breed}_{kind}.png'))
    print('ok:', breed, '<-', src, target)

# 清理不再需要的源色文件（shepherd 本身就是品种文件，保留）
for f in list(os.listdir(SRC)):
    if f.endswith('.png') and f.startswith(('white_', 'black_', 'brown_')) and not any(f.startswith(b + '_') for b in MAP):
        os.remove(os.path.join(SRC, f))
print('files:', sorted(os.listdir(SRC)))
