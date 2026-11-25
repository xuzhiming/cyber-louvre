"""Screenshots of the raised storeys: exterior, main door, grand stair, pavilion stair."""
import os, time
from playwright.sync_api import sync_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(ROOT, 'renders', 'floor_height')
os.makedirs(OUT, exist_ok=True)
URL = 'file://' + ROOT + '/web/preview.html'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 720})
    pg.goto(URL)
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=180000)
    pg.click('[data-view=hero]'); time.sleep(2.2)
    pg.screenshot(path=os.path.join(OUT, '01_exterior.png'))
    pg.click('[data-view=front]'); time.sleep(2.0)
    pg.screenshot(path=os.path.join(OUT, '02_front_door.png'))
    pg.click('[data-view=hall]'); time.sleep(2.0)
    pg.screenshot(path=os.path.join(OUT, '03_grand_stair.png'))
    pg.keyboard.press('KeyF'); time.sleep(0.8)
    pg.evaluate('window.__walk.teleport("f2")'); time.sleep(1.2)
    pg.evaluate('window.__walk.setLook(0, -0.35)'); time.sleep(0.6)
    pg.screenshot(path=os.path.join(OUT, '04_floor2_bridge.png'))
    pg.evaluate('window.__walk.teleport("b1")'); time.sleep(1.0)
    pg.evaluate('window.__walk.setLook(Math.PI, 0)'); time.sleep(0.4)
    pg.screenshot(path=os.path.join(OUT, '05_b1.png'))
    pg.evaluate('window.__walk.place(-74, 44.4, 30, 0)'); time.sleep(1.0)
    pg.evaluate('window.__walk.setLook(Math.PI/2, 0)'); time.sleep(0.4)
    pg.screenshot(path=os.path.join(OUT, '06_l4_door.png'))
    st = pg.evaluate('window.__walk.state()')
    print('L4 state', st['floor'], round(st['z'], 2))
    b.close()
print('wrote', OUT)
