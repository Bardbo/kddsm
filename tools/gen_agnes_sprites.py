# Agnes 批量生成 15 品种奔跑精灵表（与肖像同模型同描述词 → 风格贴合）
# 用法: python gen_agnes_sprites.py [breed ...]  缺省全部
import os, sys, json, urllib.request, time
from PIL import Image
import numpy as np
from collections import deque

env = {}
for line in open(os.path.expanduser('~/.hermes/.env')):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k] = v
KEY = env['AGNES_API_KEY']
BASE = env.get('AGNES_IMAGE_BASE_URL', 'https://apihub.agnes-ai.com/v1')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
FRAME = 64

BREEDS = {
    'dalmatian': '斑点狗（大麦町犬），白色毛发，身上散布大小不一的黑斑点，黑色圆耳朵，黑色圆鼻子',
    'corgi': '威尔士柯基犬，黄褐色与白色双色毛发，白色脸部与胸腹，大而直立的大耳朵，四条极短的腿，圆润可爱',
    'shiba': '柴犬，赤橙色毛发，奶油色腹部与脸颊，尖立耳，尾巴卷曲翘起，表情从容',
    'frenchy': '法国斗牛犬，浅褐色奶油色短毛，蝙蝠形大耳朵，扁平的短鼻子，健壮小身体',
    'bichon': '比熊犬，全身雪白卷曲蓬松的毛发，圆圆的脑袋，黑色圆鼻子，黑亮圆眼睛',
    'golden': '金毛寻回犬，金色柔顺长毛，垂耳，友善的眼神，尾巴蓬松',
    'collie': '边境牧羊犬，黑白色毛发，白色额头花纹与白色胸腹，中等直立耳，机警眼神',
    'samoyed': '萨摩耶犬，全身雪白蓬松毛发，标志性的微笑表情，黑鼻子，卷尾',
    'husky': '哈士奇犬，灰白双色毛发，浅蓝色眼睛，额头有白色三火花纹，白色面具，直立耳',
    'dachshund': '腊肠犬，棕色短毛，身体细长，四条极短的腿，垂耳，鼻梁长',
    'schnauzer': '雪纳瑞犬，灰色粗硬毛发，浓密的眉毛与胡须，垂耳，表情认真',
    'rottweiler': '罗威纳犬，黑色毛发配棕褐色眉斑与脸颊斑，强壮体格，半立耳',
    'tibetan': '藏獒犬，深棕色浓密长毛，颈部蓬松鬃毛，垂耳，体格壮硕，神态威严',
    'shepherd': '德国牧羊犬，黑色背部与棕色腹部四肢，直立耳，机警专注',
    'poodle': '贵宾犬，灰白色卷曲蓬松毛发，圆滚滚的头与身体，垂耳，优雅可爱',
}
STRUCT = ('奔跑动画精灵表：同一只卡通{breed}的 6 个连续奔跑动作帧，水平等距排列成一排（左到右帧1到帧6），'
          '每帧都是完整独立的全身像，侧身奔跑循环（前腿交替前伸、后腿蹬地、四腿腾空、落地缓冲），'
          '所有帧同一只狗、同一大小、同一毛色、同一侧身方向，米色纯背景，2D 卡通游戏像素风格，'
          '帧与帧之间等间距不重叠，画面内无文字无水印')

def gen(prompt):
    payload = json.dumps({"model": "agnes-image-2.0-flash", "prompt": prompt, "n": 1, "size": "1792x1024"}).encode()
    req = urllib.request.Request(f"{BASE}/images/generations", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=200) as r:
                return json.loads(r.read())['data'][0]['url']
        except Exception as e:
            if attempt == 2: raise
            time.sleep(8)

LIVELY = ('四肢动作幅度大，每帧姿态差异明显（前腿大步前伸、后腿大力蹬地、身体起伏、腾空高度变化明显），'
          '保证 6 帧是清晰不同的奔跑动作，不是相似姿势的微调')

def largest_blob(mask):
    h, w = mask.shape
    seen = np.zeros_like(mask)
    best, best_size = None, 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                q = deque([(x, y)]); seen[y, x] = 1; sz = 0; bb = [x, x, y, y]
                while q:
                    cx, cy = q.popleft(); sz += 1
                    bb[0] = min(bb[0], cx); bb[1] = max(bb[1], cx); bb[2] = min(bb[2], cy); bb[3] = max(bb[3], cy)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = 1; q.append((nx, ny))
                if sz > best_size: best, best_size = bb, sz
    return best

def flood_bg(rgb_a, tau=42):
    a = np.array(rgb_a).astype(int)
    h, w = a.shape[:2]
    total = h * w
    for _ in range(6):
        ring = np.concatenate([a[0:2].reshape(-1, 4), a[h-2:h].reshape(-1, 4), a[:, 0:2].reshape(-1, 4), a[:, w-2:w].reshape(-1, 4)])
        ring = ring[ring[:, 3] > 0]
        if len(ring) < 8: break
        med = np.median(ring[:, :3].astype(float), axis=0)
        if med.min() > 235: break
        mask = np.zeros((h, w), bool); q = deque()
        for y in range(h):
            for x in (0, w-1): q.append((x, y))
        for x in range(w):
            for y in (0, h-1): q.append((x, y))
        while q:
            x, y = q.popleft()
            if mask[y, x] or a[y, x, 3] == 0: continue
            if np.linalg.norm(a[y, x, :3].astype(float) - med) > tau: continue
            mask[y, x] = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not mask[ny, nx]: q.append((nx, ny))
        a[mask, 3] = 0
        if mask.sum() < total * 0.002: break
    return Image.fromarray(a.astype('uint8'), 'RGBA')

# 浅色/白毛品种：米色背景与浅毛距离近，tau 必须小（22）防误删；灰色系 30；深色系 42
TAU = {'corgi': 22, 'frenchy': 22, 'bichon': 22, 'golden': 22, 'husky': 22,
       'dachshund': 30, 'schnauzer': 30, 'samoyed': 22, 'dalmatian': 22}

def process_sheet(path, bid):
    im = Image.open(path).convert('RGB')
    a = np.array(im).astype(int)
    H, W = a.shape[:2]
    corners = np.concatenate([a[:5, :5].reshape(-1, 3), a[:5, -5:].reshape(-1, 3), a[-5:, :5].reshape(-1, 3), a[-5:, -5:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    dist = (np.abs(a - bg).sum(axis=2) > 90)
    rows = dist.mean(axis=1)
    ys = np.where(rows > 0.02)[0]
    if len(ys) < 10:
        print('FAIL(无内容):', bid); return False
    r0, r1 = ys.min(), ys.max()
    out = Image.new('RGBA', (FRAME * 6, FRAME), (0, 0, 0, 0))
    got = 0
    for k in range(6):
        x0, x1 = int(W * k / 6), int(W * (k + 1) / 6)
        cell = dist[r0:r1 + 1, x0:x1]
        bb = largest_blob(cell)
        if not bb: continue
        fx0, fx1, fy0, fy1 = bb
        crop = a[r0 + fy0: r0 + fy1 + 1, x0 + fx0: x0 + fx1 + 1].copy()
        fr = Image.fromarray(crop.astype('uint8'), 'RGB').convert('RGBA')
        fr = flood_bg(fr, TAU.get(bid, 42))
        b2 = fr.getbbox()
        if not b2: continue
        c = fr.crop(b2)
        sc = min(FRAME / c.width, FRAME / c.height)
        nw, nh = max(1, round(c.width * sc)), max(1, round(c.height * sc))
        c = c.resize((nw, nh), Image.NEAREST)
        cv = Image.new('RGBA', (FRAME, FRAME), (0, 0, 0, 0))
        cv.paste(c, ((FRAME - nw) // 2, (FRAME - nh) // 2))
        out.paste(cv, (k * FRAME, 0)); got += 1
    if got < 4:
        print('FAIL(帧不足):', bid, got); return False
    out.save(os.path.join(OUT, f'{bid}_run.png'))
    out.save(os.path.join(OUT, f'{bid}_jump.png'))
    out.crop((0, 0, FRAME, FRAME)).save(os.path.join(OUT, f'{bid}_idle.png'))
    print('ok:', bid, 'frames', got)
    return True

if __name__ == '__main__':
    targets = sys.argv[1:] or list(BREEDS.keys())
    for bid in targets:
        tmp = os.path.join(OUT, f'_ag_{bid}.png')
        try:
            prompt = STRUCT.replace('{breed}', BREEDS[bid])
            if bid in ('golden', 'husky', 'corgi', 'dachshund', 'tibetan'):
                prompt += '。' + LIVELY       # 动作弱的品种强制大动作差异
            url = gen(prompt)
            urllib.request.urlretrieve(url, tmp)
            process_sheet(tmp, bid)
        except Exception as e:
            print('FAIL:', bid, type(e).__name__, str(e)[:120])
        try: os.remove(tmp)
        except OSError: pass
        time.sleep(1)
    print('AGNES SPRITES DONE')
