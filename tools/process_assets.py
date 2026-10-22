# 处理 CC0 素材 → 统一 64px 帧宽图集（run 6帧/jump 6帧/idle 1帧）
# 来源：OpenGameArt Dog Spritesheets (white/black/brown, CC0, Jason of GDN) + German Shepherd (CC0, Shepardskin)
import os
from PIL import Image
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(BASE, '..', 'assets', 'dl')
OUT = os.path.join(BASE, '..', 'icons', 'dogs')
FRAME = 64

def row_bands(a):
    mask = a[..., 3] > 10
    rows = [y for y in range(mask.shape[0]) if mask[y].any()]
    bands = []
    for y in rows:
        if bands and y - bands[-1][1] <= 1: bands[-1][1] = y
        else: bands.append([y, y])
    return bands

def x_runs(rowmask):
    cols = [x for x in range(rowmask.shape[1]) if rowmask[:, x].any()]
    runs = []
    for x in cols:
        if runs and x - runs[-1][1] <= 1: runs[-1][1] = x
        else: runs.append([x, x])
    return runs

def normalize_cell(img, size=FRAME):
    """透明背景上居中缩放（保留像素感，最近邻）"""
    img = img.convert('RGBA')
    bbox = img.getbbox()
    if not bbox: return Image.new('RGBA', (size, size), (0,0,0,0))
    crop = img.crop(bbox)
    scale = min(size / crop.width, size / crop.height)
    nw, nh = max(1, round(crop.width * scale)), max(1, round(crop.height * scale))
    crop = crop.resize((nw, nh), Image.NEAREST)
    canvas = Image.new('RGBA', (size, size), (0,0,0,0))
    canvas.paste(crop, ((size - nw)//2, (size - nh)//2))
    return canvas

def sheet_from_cells(cells, n=6):
    if len(cells) < n: cells = cells + [cells[-1]] * (n - len(cells))
    cells = cells[:n]
    s = Image.new('RGBA', (FRAME * n, FRAME), (0,0,0,0))
    for i, c in enumerate(cells): s.paste(normalize_cell(c), (i * FRAME, 0))
    return s

def parse_color_sheet(fn, run_band=2, jump_band=3, idle_band=0):
    a = np.array(Image.open(fn).convert('RGBA'))
    bands = row_bands(a)
    def row_cells(bi):
        y0, y1 = bands[bi]
        rowmask = a[..., 3] > 10
        rowmask = rowmask[y0:y1+1]
        out = []
        for x0, x1 in x_runs(rowmask):
            out.append(Image.fromarray(a[y0:y1+1, x0:x1+1], 'RGBA'))
        return out
    return row_cells(run_band), row_cells(jump_band), row_cells(idle_band)

colors = ['white', 'black', 'brown']
srcs = {'white': 'spritesheet_white_0.png', 'black': 'spritesheet_black_0.png', 'brown': 'spritesheet_brown.png'}
for c in colors:
    run_cells, jump_cells, idle_cells = parse_color_sheet(os.path.join(DL, srcs[c]))
    sheet_from_cells(run_cells).save(os.path.join(OUT, f'{c}_run.png'))
    sheet_from_cells(jump_cells).save(os.path.join(OUT, f'{c}_jump.png'))
    normalize_cell(idle_cells[0]).save(os.path.join(OUT, f'{c}_idle.png'))
    print(c, 'run cells:', len(run_cells), '| jump cells:', len(jump_cells))

# 德牧：逐帧 PNG（run 5 帧补 1、default 做 idle；jump 复用 brown）
sd = os.path.join(DL, 'shepherd', 'German Shepherd', 'x1')
run = []
for i in range(1, 6):
    run.append(Image.open(os.path.join(sd, f'Shepherd_run_{i}.png')))
run.append(run[-1])   # 补第 6 帧
sheet_from_cells(run).save(os.path.join(OUT, 'shepherd_run.png'))
idle = normalize_cell(Image.open(os.path.join(sd, 'Shepherd_default.png')))
idle.save(os.path.join(OUT, 'shepherd_idle.png'))
jump_img = Image.open(os.path.join(OUT, 'brown_jump.png'))
jump_img.save(os.path.join(OUT, 'shepherd_jump.png'))
print('shepherd done')

# 清理旧的按品种生成文件
for f in list(os.listdir(OUT)):
    if f.endswith('.png') and not any(k in f for k in ('_run','_jump','_idle')):
        os.remove(os.path.join(OUT, f))
print('cleaned; remaining:', sorted(os.listdir(OUT)))
