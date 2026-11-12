"""Night look shots (t34u): exterior hero + interior gallery, night mode.  usage: night_shots.py URL TAG"""
import sys, time, json
from playwright.sync_api import sync_playwright
url, tag = sys.argv[1], sys.argv[2]
R = '/workspace/outputs/cyber_louvre/renders/art/'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': 1000, 'height': 620})
    pg.goto(url + '?minimap=0'); pg.wait_for_function('window.__ready === true', timeout=240000); pg.wait_for_function('window.__collisionReady === true', timeout=240000)
    pg.evaluate("window.__fx.setMode('night')")
    pg.evaluate("document.getElementById('ui').style.display='none'")
    pg.evaluate("window.__cam([135, 60, 150], [0, 10, -5], 35)"); time.sleep(4); pg.screenshot(path=R + f'night_ext_{tag}.png')
    pg.evaluate("window.__walk.enter(); document.getElementById('help').style.display='none'; document.getElementById('tp').style.display='none'; document.getElementById('lockmsg').style.display='none'; document.getElementById('hud').style.display='none'")
    pg.evaluate("window.__walk.place(60.1, 25.5, 8, Math.PI)"); time.sleep(25)   # 2F east gallery facing S129 wall (works loaded)
    pg.evaluate("document.getElementById('cross').style.display='none'")
    pg.screenshot(path=R + f'night_int_{tag}.png')
    print(json.dumps(pg.evaluate("window.__fx.state()"))[:400])
    b.close()
