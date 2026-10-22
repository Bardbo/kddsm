# 批量生成 15 品种卡通狗肖像（Agnes image API）
import os, json, urllib.request, time

env = {}
for line in open(os.path.expanduser('~/.hermes/.env')):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1); env[k] = v
key = env['AGNES_API_KEY']
base = env.get('AGNES_IMAGE_BASE_URL', 'https://apihub.agnes-ai.com/v1')

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
    'akita': '秋田犬，黄白色毛发，白色脸部面具，卷尾，直立耳，沉稳神态',
    'tibetan': '藏獒犬，深棕色浓密长毛，颈部蓬松鬃毛，垂耳，体格壮硕，神态威严',
    'shepherd': '德国牧羊犬，黑色背部与棕色腹部四肢，直立耳，机警专注',
    'poodle': '贵宾犬，灰白色卷曲蓬松毛发，圆滚滚的头与身体，垂耳，优雅可爱',
}

STYLE = ('可爱的卡通风格，2D 游戏立绘质感，圆润饱满的头身比例，大头短腿萌系造型，'
         '明亮的眼睛带高光，浅米色干净背景，四肢着地全身站立像，严格符合该品种的毛色花纹与体型特征')

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'dogs-ai')
os.makedirs(out_dir, exist_ok=True)

for bid, desc in BREEDS.items():
    fn = os.path.join(out_dir, f'{bid}_cartoon.png')
    if os.path.exists(fn) and os.path.getsize(fn) > 100000:
        print('skip (exists):', bid); continue
    prompt = f'一只{desc}。{STYLE}'
    payload = json.dumps({"model": "agnes-image-2.0-flash", "prompt": prompt, "n": 1, "size": "1024x1024"}).encode()
    req = urllib.request.Request(f"{base}/images/generations", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            url = json.loads(resp.read())['data'][0]['url']
        urllib.request.urlretrieve(url, fn)
        print('ok:', bid, os.path.getsize(fn)//1024, 'KB')
    except Exception as e:
        print('FAIL:', bid, e)
    time.sleep(2)
print('DONE')
