"""t39u render: renders/panel_cover.png - info panel of a video work and the audio work after click-focus: static cover only.
usage: panel_cover_shots.py URL"""
import sys, time, json, math
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
url = sys.argv[1]; R = '/workspace/outputs/cyber_louvre/renders/'
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
FL = {'L1': 0, 'L2': 8, 'L3': 16}; shots = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 720})
    pg.goto(url); pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    pg.evaluate('window.__walk.enter()'); pg.evaluate("document.getElementById('help').style.display='none'")
    for sid in ('S027', 'S129'):
        s = S[sid]; x, y = s['pos'][:2]; nx, ny = s['normal'][:2]; px, py = x + nx * 6, y + ny * 6
        pg.evaluate(f"window.__walk.place({px}, {py}, {FL[s['band']]}, {math.atan2(-(x - px), y - py)})"); pg.wait_for_function('window.__walk.state().grounded', timeout=60000); time.sleep(1.5)
        pg.mouse.click(640, 360); pg.wait_for_function('!window.__focus.state().anim', timeout=30000)
        for i in range(40):
            time.sleep(0.5); m = pg.evaluate('window.__art.media()'); e = next((e for e in m['els'] if e['slot'] == sid), None)
            if e and not e['paused'] and e['t'] > 1.5: break
        time.sleep(1.0); info = pg.evaluate('window.__art.info()'); print(sid, info['thumbTag'], info['cover'], info['media'], (info['coverSrc'] or '')[:80])
        f = f'/workspace/pc_{sid}.png'; pg.screenshot(path=f); shots.append((f, sid, info))
        pg.evaluate('window.__art.hide()')
    b.close()
f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 24)
W, H = 1280, 720; s = 0.62; w, h = int(W * s), int(H * s)
out = Image.new('RGB', (w * 2 + 30, h + 50), (12, 10, 24)); d = ImageDraw.Draw(out)
for k, (fn, sid, info) in enumerate(shots):
    out.paste(Image.open(fn).convert('RGB').resize((w, h)), (10 + k * (w + 10), 44))
    d.text((10 + k * (w + 10), 8), ('视频作品' if sid == 'S027' else '音频作品') + f' {sid}:墙上照常播放,介绍框只显示静态封面', fill=(255, 190, 245), font=f)
out.save(R + 'panel_cover.png'); print(R + 'panel_cover.png')
