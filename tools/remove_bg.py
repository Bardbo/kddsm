# 抠掉 AI 精灵表的米色背景：边缘洪水填充(8连通,颜色距离) → alpha=0，保留狗本体（含白毛）
# 只清与帧边缘连通的背景像素，狗内部的白毛因不连通边缘而保留
import os
from PIL import Image
import numpy as np
from collections import deque

FRAME = 64
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
BREEDS = ['dalmatian','corgi','shiba','frenchy','bichon','golden','collie','samoyed',
          'husky','dachshund','schnauzer','rottweiler','tibetan','shepherd','poodle']

def flood_remove_bg(frame_rgba, tau=42):
    """多轮边缘剥离：每轮取当前仍不透明像素的边缘主色为背景色，从四边洪水填充清除，
    直到某轮清除量过小（狗毛贴近边缘，主体颜色到达边界）或边界主色接近纯白（怕误吃白毛）时停止。"""
    a = np.array(frame_rgba)
    h, w = a.shape[:2]
    total = h * w
    for _ in range(6):
        # 当前边缘 2px 环（只取仍不透明的）
        ring = np.concatenate([a[0:2].reshape(-1, 4), a[h-2:h].reshape(-1, 4),
                               a[:, 0:2].reshape(-1, 4), a[:, w-2:w].reshape(-1, 4)])
        ring = ring[ring[:, 3] > 0]
        if len(ring) < 8: break
        med = np.median(ring[:, :3].astype(float), axis=0)
        if med.min() > 235: break                                   # 边界已是白毛/白底，停
        mask = np.zeros((h, w), bool)
        q = deque()
        for y in range(h):
            for x in (0, w - 1): q.append((x, y))
        for x in range(w):
            for y in (0, h - 1): q.append((x, y))
        while q:
            x, y = q.popleft()
            if mask[y, x] or a[y, x, 3] == 0: continue
            px = a[y, x, :3].astype(float)
            if np.linalg.norm(px - med) > tau: continue
            mask[y, x] = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not mask[ny, nx]:
                        q.append((nx, ny))
        a[mask, 3] = 0
        if mask.sum() < total * 0.002: break                        # 本轮几乎没清除 → 停
    return Image.fromarray(a, 'RGBA')

def process(path):
    im = Image.open(path).convert('RGBA')
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for i in range(im.width // FRAME):
        f = im.crop((i * FRAME, 0, (i + 1) * FRAME, im.height))
        out.paste(flood_remove_bg(f), (i * FRAME, 0))
    out.save(path)

if __name__ == '__main__':
    for b in BREEDS:
        for suf in ('run', 'jump', 'idle'):
            p = os.path.join(OUT, f'{b}_{suf}.png')
            if os.path.exists(p): process(p)
        print('ok:', b)
    print('DONE')
