# 奔跑帧重锚定：所有帧按"躯干中心"（上部 50% 不透明像素加权中心）对齐到 64x64 帧中心
# 解决：切帧时按包围盒独立居中 → 腿张开时躯干被挤偏 → 奔跑时狗身左右晃（闪屏）
import os
import numpy as np
from PIL import Image

FRAME = 64
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
BREEDS = ['dalmatian','corgi','shiba','frenchy','bichon','golden','collie','samoyed',
          'husky','dachshund','schnauzer','rottweiler','tibetan','shepherd','poodle']

def reanchor_frame(f):
    a = np.array(f).astype(float)
    m = a[..., 3] > 128
    ys, xs = np.where(m)
    if len(xs) < 4:
        return f
    top, bottom = ys.min(), ys.max()
    # 躯干区 = 包围盒上部（头+躯干，腿在下半不参与锚定；比例 0.4：蓬松颈鬃/长毛品种更聚焦头身，锚定更稳）
    torso_top = top
    torso_bottom = top + max(1, int((bottom - top) * 0.4))
    tm = m.copy(); tm[torso_bottom:, :] = False
    ty, tx = np.where(tm)
    if len(tx) == 0:
        tx, ty = xs, ys
    w = a[ty, tx, 3] + 1e-6                     # 用 alpha 加权（实心 255）
    cx = (tx * w).sum() / w.sum()
    cy = (ty * w).sum() / w.sum()
    dx = int(round(FRAME / 2 - cx))
    dy = int(round(FRAME / 2 - cy))
    out = np.zeros((FRAME, FRAME, 4), dtype=np.uint8)
    for oy in range(FRAME):
        sy = oy - dy
        if sy < 0 or sy >= FRAME: continue
        for ox in range(FRAME):
            sx = ox - dx
            if sx < 0 or sx >= FRAME: continue
            if a[sy, sx, 3] > 0:
                out[oy, ox] = a[sy, sx]
    return Image.fromarray(out, 'RGBA')

for b in BREEDS:
    for suf in ('run', 'jump', 'idle'):
        p = os.path.join(OUT, f'{b}_{suf}.png')
        if not os.path.exists(p): continue
        im = Image.open(p).convert('RGBA')
        out = Image.new('RGBA', im.size, (0, 0, 0, 0))
        for i in range(im.width // FRAME):
            out.paste(reanchor_frame(im.crop((i * FRAME, 0, (i + 1) * FRAME, im.height))), (i * FRAME, 0))
        out.save(p)
    print('ok:', b)
print('REANCHOR DONE')
