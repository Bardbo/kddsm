# 批量生成 15 品种专属奔跑精灵表（GPT Image 2.5，同品种 6 帧循环）→ 切帧 → icons/dogs/{breed}_{run,jump,idle}.png
import os, json, urllib.request, time
from PIL import Image
import numpy as np

# ---- 环境 ----
env = {}
for line in open(os.path.expanduser('~/.hermes/.env')):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k] = v
KEY = env['GRSAI_API_KEY']
BASE = env.get('GRSAI_BASE_URL', 'https://grsai.dakka.com.cn')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
FRAME = 64

BREEDS = {
    'dalmatian': '斑点狗（大麦町犬），白色毛发，散布大小不一的黑斑点，黑色圆耳朵，黑色圆鼻子',
    'corgi': '威尔士柯基犬，黄褐色与白色双色毛发，白色脸部与胸腹，大立耳，四条极短的腿，圆润',
    'shiba': '柴犬，赤橙色毛发，奶油色腹部与脸颊，尖立耳，尾巴卷曲翘起',
    'frenchy': '法国斗牛犬，浅褐色奶油色短毛，蝙蝠形大耳朵，扁平短鼻子，健壮小身体',
    'bichon': '比熊犬，全身雪白卷曲蓬松毛发，圆脑袋，黑色圆鼻子，黑亮圆眼睛',
    'golden': '金毛寻回犬，金色柔顺长毛，垂耳，友善眼神，蓬松尾巴',
    'collie': '边境牧羊犬，黑白色毛发，白色额头流星纹与白色胸腹，直立耳，机警眼神',
    'samoyed': '萨摩耶犬，全身雪白蓬松毛发，标志性微笑表情，黑鼻子，卷尾',
    'husky': '哈士奇犬，灰白双色毛发，浅蓝色眼睛，额头白色三火花纹，白色面具，直立耳',
    'dachshund': '腊肠犬，棕色短毛，身体细长，四条极短腿，垂耳，长鼻梁',
    'schnauzer': '雪纳瑞犬，灰色粗硬毛发，浓密眉毛与胡须，垂耳，表情认真',
    'rottweiler': '罗威纳犬，黑色毛发配棕褐色眉斑与脸颊斑，强壮的体格，直立或半立耳',
    'tibetan': '藏獒犬，深棕色浓密长毛，颈部蓬松鬃毛，垂耳，体格壮硕，神态威严',
    'shepherd': '德国牧羊犬，黑色背部与棕色腹部四肢，直立耳，机警专注',
    'poodle': '贵宾犬，灰白色卷曲蓬松毛发，圆滚滚头与身体，垂耳，优雅可爱',
}
STRUCT = ('奔跑动画精灵表：同一只卡通{breed}的 6 个连续奔跑动作帧，水平等距排列成一排（左到右帧1到帧6），'
          '每帧都是完整独立的全身像，侧身奔跑循环（前腿交替前伸、后腿蹬地、四腿腾空、落地缓冲），'
          '所有帧同一只狗、同一大小、同一毛色、同一侧身方向，米色纯背景，2D 卡通游戏像素风格，'
          '帧与帧之间等间距不重叠，画面内无文字无水印')

def gen(prompt):
    payload = json.dumps({"model": "gpt-image-2.5", "prompt": prompt, "aspectRatio": "16:9", "quality": "auto", "replyType": "json"}).encode()
    req = urllib.request.Request(f"{BASE}/v1/api/generate", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    tid = d.get('id')
    for _ in range(60):
        time.sleep(10)
        req2 = urllib.request.Request(f"{BASE}/v1/api/result?id={tid}",
            headers={"Authorization": f"Bearer {KEY}"}, method="GET")
        with urllib.request.urlopen(req2, timeout=30) as r2:
            d2 = json.loads(r2.read())
        st = d2.get('status')
        if st == 'succeeded':
            return d2['results'][0]['url']
        if st in ('failed', 'violation'):
            raise RuntimeError(f"status={st}: {d2.get('error')}")
    raise RuntimeError('timeout polling')

def slice_frames(img):
    """把 16:9 精灵表切成 6 帧：水平 6 等分 → 每段裁到 alpha 包围盒"""
    a = np.array(img.convert('RGBA'))
    H, W = a.shape[:2]
    frames = []
    for k in range(6):
        x0, x1 = int(W * k / 6), int(W * (k + 1) / 6)
        cell = a[:, x0:x1]
        alpha = cell[..., 3] > 10
        ys, xs = np.where(alpha)
        if len(xs) == 0:
            frames.append(None); continue
        c0, c1 = xs.min(), xs.max(); r0, r1 = ys.min(), ys.max()
        frames.append(Image.fromarray(a[r0:r1 + 1, x0 + c0:x0 + c1 + 1], 'RGBA'))
    return frames

def norm(img):
    bbox = img.getbbox()
    if not bbox: return Image.new('RGBA', (FRAME, FRAME), (0,0,0,0))
    c = img.crop(bbox)
    sc = min(FRAME / c.width, FRAME / c.height)
    nw, nh = max(1, round(c.width * sc)), max(1, round(c.height * sc))
    c = c.resize((nw, nh), Image.NEAREST)
    cv = Image.new('RGBA', (FRAME, FRAME), (0,0,0,0))
    cv.paste(c, ((FRAME - nw) // 2, (FRAME - nh) // 2))
    return cv

for bid, desc in BREEDS.items():
    try:
        prompt = STRUCT.replace('{breed}', desc)
        url = gen(prompt)
        tmp = os.path.join(OUT, f'_tmp_{bid}.png')
        urllib.request.urlretrieve(url, tmp)
        im = Image.open(tmp).convert('RGBA')
        frames = [f for f in slice_frames(im) if f is not None]
        if len(frames) < 4:
            print('FAIL(帧不足):', bid, len(frames)); os.remove(tmp); continue
        frames = frames[:6]
        run = Image.new('RGBA', (FRAME * 6, FRAME), (0,0,0,0))
        for i, f in enumerate(frames):
            run.paste(norm(f), (i * FRAME, 0))
        run.save(os.path.join(OUT, f'{bid}_run.png'))
        run.save(os.path.join(OUT, f'{bid}_jump.png'))      # 跳跃复用奔跑帧（CSS 弧线负责上抛）
        norm(frames[0]).save(os.path.join(OUT, f'{bid}_idle.png'))
        os.remove(tmp)
        print('ok:', bid)
    except Exception as e:
        print('FAIL:', bid, e)
print('DONE')
