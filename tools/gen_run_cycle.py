# 把 ImageGen 生成的「同品种 6 帧奔跑精灵表」处理成 icons/dogs/{breed}_run.png
# 与旧脚本的差别（旧脚本的三个坑）：
#   ① 水平等分切帧 → 模型排布不均时会把相邻狗切进来（罗威纳那套就有花狗串帧）
#   ② 每帧独立缩放到填满 64×64 → 帧间大小抖动，跑起来像在"呼吸"
#   ③ 定死 6 帧 → 生成 5 帧时末帧被裁
# 这里改为：整图去底 → 按"空列"聚类出真实帧 → 全帧统一缩放 → 脚底基线对齐 → 输出 128px/帧（2x，Retina 清晰）
import os, sys, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'icons', 'dogs')
FRAME = 128          # 每帧边长（CSS 仍按 64px 显示，等价 2x）
MARGIN = 3           # 帧内留白，避免贴边


def bg_remove(im, tau=34):
    """从四边洪水填充去掉米色底。狗的白色毛发被黑色描边包围，不与边缘连通 → 不会被吃掉。"""
    im = im.convert('RGBA')
    w, h = im.size
    px = im.load()
    # 以四边中位色作为背景色
    ring = []
    for x in range(0, w, 3):
        ring.append(px[x, 0]); ring.append(px[x, h - 1])
    for y in range(0, h, 3):
        ring.append(px[0, y]); ring.append(px[w - 1, y])
    br = sorted(p[0] for p in ring)[len(ring) // 2]
    bg_ = sorted(p[1] for p in ring)[len(ring) // 2]
    bb = sorted(p[2] for p in ring)[len(ring) // 2]
    seen = bytearray(w * h)
    stack = []
    for x in range(w):
        stack.append((x, 0)); stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y)); stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, a = px[x, y]
        if abs(r - br) + abs(g - bg_) + abs(b - bb) > tau:
            continue
        px[x, y] = (r, g, b, 0)
        if x > 0: stack.append((x - 1, y))
        if x < w - 1: stack.append((x + 1, y))
        if y > 0: stack.append((x, y - 1))
        if y < h - 1: stack.append((x, y + 1))
    return im


def dog_band(im):
    """按行前景密度找"狗所在的那一条横带"，把右下角的 AI 水印/说明文字排除掉。
    狗身每行有上百个前景像素，水印文字只有几十个 → 用最大行密度的 20% 作阈值即可分开。"""
    w, h = im.size
    px = im.load()
    rows = [0] * h
    for y in range(h):
        c = 0
        for x in range(w):
            if px[x, y][3] > 16:
                c += 1
        rows[y] = c
    mx = max(rows) if rows else 0
    if mx == 0:
        return 0, h - 1
    thr = max(6, int(mx * 0.2))
    ys = [y for y in range(h) if rows[y] >= thr]
    if not ys:
        return 0, h - 1
    return max(0, ys[0] - 2), min(h - 1, ys[-1] + 2)


def components(im, min_area=300):
    """连通域切帧：比"按空列切"稳得多——模型偶尔把两帧画得贴在一起（空列消失），
    或者干脆排成两行，按列切都会串帧。每只狗是一个独立连通域，面积过滤顺手把水印文字丢掉。"""
    w, h = im.size
    px = im.load()
    seen = bytearray(w * h)
    out = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0 * w + x0] or px[x0, y0][3] <= 16:
                continue
            stack = [(x0, y0)]
            seen[y0 * w + x0] = 1
            minx, maxx, miny, maxy, area = x0, x0, y0, y0, 0
            while stack:
                x, y = stack.pop()
                area += 1
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if nx < 0 or nx >= w:
                        continue
                    for dy in (-1, 0, 1):
                        ny = y + dy
                        if ny < 0 or ny >= h:
                            continue
                        i = ny * w + nx
                        if seen[i] or px[nx, ny][3] <= 16:
                            continue
                        seen[i] = 1
                        stack.append((nx, ny))
            if area >= min_area:
                out.append((minx, miny, maxx + 1, maxy + 1, area))
    return out


def normalize(frames):
    """逐帧按"高度"归一到同一标尺（保持宽高比），脚底基线对齐、水平居中。
    —— 不能每帧都缩到填满方框（旧脚本的坑：帧间大小抖动，跑起来像在呼吸）；也不能只用一个比例，
    因为模型偶尔会把某一帧画小一点。按高度归一 = 身体大小一致，迈腿幅度差异仍然保留。"""
    box = FRAME - MARGIN * 2
    target_h = int(box * 0.94)
    out = []
    for f in frames:
        s = min(target_h / f.height, box / f.width)
        nw, nh = max(1, round(f.width * s)), max(1, round(f.height * s))
        r = f.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new('RGBA', (FRAME, FRAME), (0, 0, 0, 0))
        canvas.paste(r, ((FRAME - nw) // 2, FRAME - MARGIN - nh), r)   # 脚底基线对齐
        out.append(canvas)
    return out


def trim(im, box):
    c = im.crop(box)
    bb = c.getbbox()
    if not bb:
        return None
    return (box[0] + bb[0], box[1] + bb[1], box[0] + bb[2], box[1] + bb[3], 0)


def split_merged(im, boxes):
    """两只狗贴在一起时连通域会并成一个（牧羊犬那套就是尾巴搭在一起）→ 在中间找"最空的一列"劈开。"""
    widths = sorted(b[2] - b[0] for b in boxes)
    if not widths:
        return boxes
    med = widths[len(widths) // 2]
    px = im.load()
    out = []
    for b in boxes:
        w = b[2] - b[0]
        if w > med * 1.45:
            best = None
            for x in range(b[0] + int(w * 0.3), b[0] + int(w * 0.7)):
                c = 0
                for y in range(b[1], b[3]):
                    if px[x, y][3] > 16:
                        c += 1
                if best is None or c < best[0]:
                    best = (c, x)
            if best and best[0] <= (b[3] - b[1]) * 0.12:
                x = best[1]
                for half in ((b[0], b[1], x, b[3], 0), (x, b[1], b[2], b[3], 0)):
                    t = trim(im, half)
                    if t:
                        out.append(t)
                continue
        out.append(b)
    return out


def collect_frames(im):
    """连通域 → 按行分组 → 行内按 x 排序（兼容模型排成两行的情况），丢弃水印级别的小碎片。"""
    comps = components(im, min_area=max(300, int(im.width * im.height * 0.0006)))
    if not comps:
        return []
    max_area = max(b[4] for b in comps)
    comps = [b for b in comps if b[4] >= max_area * 0.18]
    comps = split_merged(im, comps)
    rows = []
    for b in sorted(comps, key=lambda b: b[1]):
        cy = (b[1] + b[3]) / 2
        hh = b[3] - b[1]
        for r in rows:
            if abs(r['cy'] - cy) < hh * 0.6:
                r['items'].append(b)
                r['cy'] = (r['cy'] + cy) / 2
                break
        else:
            rows.append({'cy': cy, 'items': [b]})
    rows.sort(key=lambda r: r['cy'])
    ordered = []
    for r in rows:
        ordered.extend(sorted(r['items'], key=lambda b: b[0]))
    return [im.crop(b[:4]) for b in ordered[:6]]


def build(sheet_path, breed, out_path=None):
    im = Image.open(sheet_path).convert('RGBA')
    im = bg_remove(im)
    y0, y1 = dog_band(im)
    im = im.crop((0, y0, im.width, y1 + 1))       # 只留狗所在横带（去掉右下角水印）
    frames = collect_frames(im)
    if len(frames) < 4:
        raise RuntimeError(f'{breed}: 只切出 {len(frames)} 帧，放弃（请重生成）')
    frames = normalize(frames)
    sheet = Image.new('RGBA', (FRAME * len(frames), FRAME), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * FRAME, 0), f)
    dst = out_path or os.path.join(OUT, f'{breed}_run.png')
    sheet.save(dst)
    # 跳跃复用同一组帧（上抛弧线由 CSS 负责）→ 不再单独写 _jump.png；idle 取首帧
    frames[0].save(os.path.join(OUT, f'{breed}_idle.png'))
    return len(frames)


if __name__ == '__main__':
    # 默认按 assets/dogs-ai/sheets/index.json 全量重做；也可以只跑指定品种：
    #   python tools/gen_run_cycle.py corgi husky
    sheet_dir = os.path.join(ROOT, 'assets', 'dogs-ai', 'sheets')
    with open(os.path.join(sheet_dir, 'index.json'), encoding='utf-8') as f:
        pairs = {b: os.path.join(sheet_dir, n) for b, n in json.load(f).items()}
    wanted = sys.argv[1:]
    if wanted:
        pairs = {b: p for b, p in pairs.items() if b in wanted}
    for breed, sheet in pairs.items():
        try:
            n = build(sheet, breed)
            print(f'ok: {breed} -> {n} 帧')
        except Exception as e:
            print(f'FAIL: {breed} {e}')
