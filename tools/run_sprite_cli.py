# 用已验证的 grsai_img.py CLI 逐品种生成精灵表 → 切帧 → 组装动画
import os, subprocess, sys, time
from PIL import Image
import numpy as np

CLI = r'C:\Users\Administrator\Desktop\grsai\grsai_img.py'
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

def crop_sheet(path, bid):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    frames = []
    for k in range(6):
        x0, x1 = int(W * k / 6), int(W * (k + 1) / 6)
        cell = a[:, x0:x1]
        alpha = cell[..., 3] > 10
        ys, xs = np.where(alpha)
        if len(xs) == 0: continue
        c0, c1 = xs.min(), xs.max(); r0, r1 = ys.min(), ys.max()
        frames.append(Image.fromarray(a[r0:r1 + 1, x0 + c0:x0 + c1 + 1], 'RGBA'))
    if len(frames) < 4:
        print('FAIL(帧不足):', bid, len(frames)); return False
    run = Image.new('RGBA', (FRAME * 6, FRAME), (0,0,0,0))
    for i, f in enumerate(frames[:6]):
        bbox = f.getbbox()
        c = f.crop(bbox)
        sc = min(FRAME / c.width, FRAME / c.height)
        nw, nh = max(1, round(c.width * sc)), max(1, round(c.height * sc))
        c = c.resize((nw, nh), Image.NEAREST)
        cv = Image.new('RGBA', (FRAME, FRAME), (0,0,0,0))
        cv.paste(c, ((FRAME - nw) // 2, (FRAME - nh) // 2))
        run.paste(cv, (i * FRAME, 0))
    run.save(os.path.join(OUT, f'{bid}_run.png'))
    run.save(os.path.join(OUT, f'{bid}_jump.png'))
    frames[0].save(os.path.join(OUT, f'{bid}_idle.png'))
    return True

for bid, desc in BREEDS.items():
    tmp = os.path.join(OUT, f'_sheet_{bid}.png')
    prompt = STRUCT.replace('{breed}', desc)
    r = subprocess.run([sys.executable, CLI, prompt, '--model', 'gpt-image-2.5', '--ratio', '16:9',
                        '--out', tmp, '--node', 'cn'], capture_output=True, text=True, timeout=400)
    if r.returncode != 0 or not os.path.exists(tmp):
        print('FAIL(gen):', bid, (r.stderr or r.stdout or '').strip()[:200]); continue
    ok = crop_sheet(tmp, bid)
    try: os.remove(tmp)
    except OSError: pass
    print('ok:' if ok else 'fail:', bid)
    time.sleep(2)
print('DONE')
