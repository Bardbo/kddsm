# 每帧狗重新归一化填满 64px（当前帧里狗只有 ~16px，重放大到占满帧）→ 再跑多轮抠背景
import os
from PIL import Image
import numpy as np
from remove_bg import flood_remove_bg

FRAME = 64
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
BREEDS = ['dalmatian','corgi','shiba','frenchy','bichon','golden','collie','samoyed',
          'husky','dachshund','schnauzer','rottweiler','tibetan','shepherd','poodle']

def renorm(path):
    im = Image.open(path).convert('RGBA')
    out = Image.new('RGBA', (im.width, im.height), (0, 0, 0, 0))
    for i in range(im.width // FRAME):
        f = im.crop((i * FRAME, 0, (i + 1) * FRAME, im.height))
        bbox = f.getbbox()
        if not bbox:
            out.paste(f, (i * FRAME, 0)); continue
        c = f.crop(bbox)
        sc = min(FRAME / c.width, FRAME / c.height)
        nw, nh = max(1, round(c.width * sc)), max(1, round(c.height * sc))
        c = c.resize((nw, nh), Image.NEAREST)
        cv = Image.new('RGBA', (FRAME, FRAME), (0, 0, 0, 0))
        cv.paste(c, ((FRAME - nw) // 2, (FRAME - nh) // 2))
        out.paste(cv, (i * FRAME, 0))
    out.save(path)

for b in BREEDS:
    for suf in ('run', 'jump', 'idle'):
        p = os.path.join(OUT, f'{b}_{suf}.png')
        if os.path.exists(p): renorm(p)
    # 再抠背景（多轮剥离）
    for suf in ('run', 'jump', 'idle'):
        p = os.path.join(OUT, f'{b}_{suf}.png')
        if os.path.exists(p):
            im = Image.open(p).convert('RGBA')
            out = Image.new('RGBA', im.size, (0, 0, 0, 0))
            for i in range(im.width // FRAME):
                f = im.crop((i * FRAME, 0, (i + 1) * FRAME, im.height))
                out.paste(flood_remove_bg(f), (i * FRAME, 0))
            out.save(p)
    # 统计
    im = np.array(Image.open(os.path.join(OUT, f'{b}_run.png')).convert('RGBA'))
    a = im[..., 3] > 128
    ys, xs = np.where(a)
    print(f"{b:<10} opaque%={a.mean()*100:5.1f} bbox=({xs.min()}-{xs.max()},{ys.min()}-{ys.max()})" if len(xs) else b + ' EMPTY')
print('DONE')
