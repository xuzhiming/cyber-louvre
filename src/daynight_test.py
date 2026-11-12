import json, time, math
from playwright.sync_api import sync_playwright
ROOT = '/workspace/outputs/cyber_louvre/'; SH = ROOT + 'renders/daynight/'
import os; os.makedirs(SH, exist_ok=True)
errors = []; out = {}
def L(*a): print(*a, flush=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 960, 'height': 540})
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append('PAGEERROR ' + str(e)))
    pg.goto('file://' + ROOT + 'web/preview.html')
    pg.wait_for_function('window.__ready === true && window.__collisionReady === true', timeout=240000)
    fx = lambda: pg.evaluate('window.__fx.state()')
    def shot(n): time.sleep(1.5); pg.screenshot(path=SH + n + '.png', timeout=180000)
    def vis(sel): return pg.evaluate("(s)=>{const r=document.querySelector(s).getBoundingClientRect();return r.width>0&&r.right<=innerWidth&&r.bottom<=innerHeight&&r.left>=0}", sel)
    pg.evaluate("window.__goTo('hero')"); time.sleep(3)
    out['orbit_buttons_visible'] = [vis('#fxMode'), vis('#fxLights'), vis('#fxBloom')]
    out['night'] = fx(); shot('orbit_night')
    pg.keyboard.press('KeyL'); out['night_lights_off'] = fx(); shot('orbit_night_lightsoff')
    pg.keyboard.press('KeyL'); pg.keyboard.press('KeyN'); out['day'] = fx(); shot('orbit_day')
    pg.keyboard.press('KeyL'); out['day_lights_off'] = fx(); shot('orbit_day_lightsoff'); pg.keyboard.press('KeyL')
    pg.keyboard.press('KeyB'); out['day_bloom_off'] = fx(); pg.keyboard.press('KeyB')
    pg.keyboard.press('KeyH'); out['help_orbit_visible'] = pg.evaluate("getComputedStyle(document.getElementById('help')).display"); pg.keyboard.press('KeyH')
    # button clicks
    pg.click('#fxMode'); out['click_mode_night'] = fx()['mode']; pg.click('#fxMode')
    # walk mode, interior viewpoint
    pg.keyboard.press('KeyF'); time.sleep(1.5)
    pg.evaluate('window.__walk.teleport("lobby")'); time.sleep(1); pg.evaluate('window.__walk.setLook(0, 0.15)')
    out['walk_buttons_visible'] = [vis('#fxMode'), vis('#fxLights'), vis('#fxBloom')]
    out['walk_day'] = fx(); shot('walk_lobby_day')
    pg.keyboard.press('KeyN'); out['walk_night'] = fx(); shot('walk_lobby_night')
    pg.keyboard.press('KeyL'); out['walk_night_off'] = fx(); shot('walk_lobby_night_lightsoff'); pg.keyboard.press('KeyL')
    s0 = pg.evaluate('window.__walk.state()'); pg.keyboard.down('KeyW'); time.sleep(3); pg.keyboard.up('KeyW'); s1 = pg.evaluate('window.__walk.state()')
    out['walk_moved_m'] = round(math.hypot(s1['x'] - s0['x'], s1['y'] - s0['y']), 2); out['walk_state'] = [round(s1['x'],2), round(s1['y'],2), round(s1['z'],2), s1['grounded']]
    pg.keyboard.press('KeyN'); pg.keyboard.down('KeyW'); time.sleep(1.5); pg.keyboard.up('KeyW'); s2 = pg.evaluate('window.__walk.state()')
    out['walk_moved_in_day_m'] = round(math.hypot(s2['x'] - s1['x'], s2['y'] - s1['y']), 2)
    pg.keyboard.press('KeyH'); out['help_walk_toggle'] = pg.evaluate("getComputedStyle(document.getElementById('help')).display")
    out['errors'] = errors
    L(json.dumps(out, indent=1, default=str)); json.dump(out, open(SH + 'daynight_test.json', 'w'), indent=1, default=str)
    b.close()
