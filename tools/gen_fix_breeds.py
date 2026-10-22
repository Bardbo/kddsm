# 5 只问题品种用金毛验证配方重生成：2.1-flash + 逐帧姿势描述（保证 6 帧差异明显且连贯）
import os, sys, json, urllib.request, time

env = {}
for line in open(os.path.expanduser('~/.hermes/.env')):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k] = v
KEY = env['AGNES_API_KEY']
BASE = env.get('AGNES_IMAGE_BASE_URL', 'https://apihub.agnes-ai.com/v1')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_agnes_sprites import process_sheet, BREEDS

POSES = ('帧1=后腿大力蹬地身体前倾，帧2=前腿前伸落地，帧3=四腿腾空收拢，帧4=落地缓冲四肢展开，'
         '帧5=后腿前摆换步，帧6=回到帧1姿态。每一帧的腿部位置和身体角度都必须明显不同，'
         '四肢清晰可辨，禁止相似姿势重复。米色纯背景，2D 卡通游戏像素风格，无文字无水印')

def gen(prompt):
    payload = json.dumps({"model": "agnes-image-2.1-flash", "prompt": prompt, "n": 1, "size": "1792x1024"}).encode()
    req = urllib.request.Request(f"{BASE}/images/generations", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read())['data'][0]['url']
        except Exception as e:
            if attempt == 2: raise
            time.sleep(8)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icons', 'dogs')
targets = sys.argv[1:] or ['collie', 'rottweiler', 'tibetan', 'husky', 'dachshund']
for bid in targets:
    tmp = os.path.join(OUT, f'_ag2_{bid}.png')
    try:
        prompt = (f'奔跑动画精灵表：同一只卡通{BREEDS[bid]}的 6 个连续奔跑动作帧，水平等距排列（左到右帧1到帧6）。'
                  f'{POSES}')
        url = gen(prompt)
        urllib.request.urlretrieve(url, tmp)
        process_sheet(tmp, bid)
        print('ok:', bid)
    except Exception as e:
        print('FAIL:', bid, type(e).__name__, str(e)[:150])
    try: os.remove(tmp)
    except OSError: pass
    time.sleep(1)
print('FIX BREEDS DONE')
