"""t37u render: renders/click_focus.png = before click (6 m away, at an angle, cursor on the work) | after focus (camera in front
+ info panel).  usage: click_focus_shots.py URL [SLOT]"""
import sys, time, json, math
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
url = sys.argv[1]; sid = sys.argv[2] if len(sys.argv) > 2 else 'S047'; R = '/workspace/outputs/cyber_louvre/renders/'
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
s = S[sid]; x, y = s['pos'][:2]; nx, ny = s['normal'][:2]; tx, ty = -ny, nx; FL = {'L1': 0, 'L2': 8, 'L3': 16}[s['band']]
px, py = x + nx * 6 + tx * 2.2, y + ny * 6 + ty * 2.2; yaw = math.atan2(-(x - px), y - py) + 0.25
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 720})
    pg.goto(url); pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate('window.__walk.enter()'); pg.evaluate("document.getElementById('help').style.display='none'")
    pg.evaluate(f"window.__walk.place({px}, {py}, {FL}, {yaw})"); pg.wait_for_function('window.__walk.state().grounded', timeout=60000)
    pg.wait_for_function(f"['loaded','failed'].includes(window.__art.slot('{sid}').state)", timeout=60000); time.sleep(2.5)
    pr = pg.evaluate(f"window.__focus.project('{sid}')"); pg.mouse.move(pr['x'], pr['y']); time.sleep(0.3)
    pg.screenshot(path='/tmp/cfs_before.png')
    pg.mouse.down(); pg.mouse.up(); time.sleep(0.4); pg.screenshot(path='/tmp/cfs_mid.png')
    pg.wait_for_function('!window.__focus.state().anim', timeout=30000); time.sleep(3.0)
    pg.evaluate("document.querySelectorAll('#artinfo details').forEach(d => d.open = true)"); time.sleep(0.3)
    pg.screenshot(path='/tmp/cfs_after.png'); print(pg.evaluate(f"window.__focus.pose('{sid}')"), pg.evaluate('window.__art.info()')['title'])
    b.close()
ims = [Image.open(f'/tmp/cfs_{k}.png').convert('RGB') for k in ('before', 'mid', 'after')]
W, H = ims[0].size; sc = 0.5; w2, h2 = int(W * sc), int(H * sc)
out = Image.new('RGB', (w2 * 2 + 30, h2 + int(H * 0.75) + 110), (12, 10, 24)); d = ImageDraw.Draw(out)
try: f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 26)
except Exception: f = ImageFont.load_default()
d.text((10, 8), '① 点击前:6 米外斜看,鼠标指向作品', fill=(255, 190, 245), font=f); out.paste(ims[0].resize((w2, h2)), (10, 44))
d.text((w2 + 20, 8), '② 左键点击后镜头平滑移动中(约 0.9 秒)', fill=(255, 190, 245), font=f); out.paste(ims[1].resize((w2, h2)), (w2 + 20, 44))
y2 = h2 + 60; d.text((10, y2), '③ 到位:正对作品、视线居中,右侧弹出作品介绍(作品介绍 / 标签 / 策展人点评 / 艺术家简介 / 链接)', fill=(255, 190, 245), font=f)
big = ims[2].resize((int(W * 0.75), int(H * 0.75))); out.paste(big, ((out.width - big.width) // 2, y2 + 40))
out.save(R + 'click_focus.png'); print(R + 'click_focus.png', out.size)
