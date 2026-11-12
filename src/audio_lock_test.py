"""Autoplay-blocked path (t33u): emulate the browser policy (play() rejects with NotAllowedError until the page has had a trusted
user gesture), walk near the audio work, expect the hint, click it, expect playback.  usage: audio_lock_test.py URL"""
import sys, time, json, math
from playwright.sync_api import sync_playwright
url = sys.argv[1]
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
s = S['S129']; x, y, z = s['pos']; nx, ny = s['normal'][:2]; yaw = math.atan2(nx, -ny)
INIT = """(() => { window.__gest = false; for (const t of ['pointerdown', 'keydown', 'click']) addEventListener(t, (e) => { if (e.isTrusted) window.__gest = true; }, true);
  const orig = HTMLMediaElement.prototype.play; HTMLMediaElement.prototype.play = function () {
  if (this instanceof HTMLAudioElement && !window.__gest) return Promise.reject(new DOMException('play() blocked (emulated autoplay policy)', 'NotAllowedError'));
  return orig.apply(this, arguments); }; })();"""
res, cons = {}, []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1280, 'height': 760}); pg.add_init_script(INIT)
    pg.on('console', lambda m: cons.append((m.type, m.text[:200])) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: cons.append(('pageerror', str(e)[:200])))
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000); pg.wait_for_function('window.__collisionReady === true', timeout=240000)
    res['activated_before'] = pg.evaluate('window.__gest')
    pg.evaluate("window.__walk.enter()"); pg.evaluate(f"window.__walk.place({x + nx * 3}, {y + ny * 3}, 8, {yaw})"); time.sleep(6)
    res['locked'] = pg.evaluate("window.__art.audioState()"); res['audio_locked'] = pg.evaluate("window.__art.audio('S129')")
    res['hint_visible'] = pg.is_visible('#audiohint')
    pg.screenshot(path='/workspace/outputs/cyber_louvre/renders/art/audio_locked_hint.png')
    if res['hint_visible']: pg.click('#audiohint')
    time.sleep(3); a1 = pg.evaluate("window.__art.audio('S129')"); time.sleep(2); a2 = pg.evaluate("window.__art.audio('S129')")
    res['after_click'] = [a1, a2]; res['state_after'] = pg.evaluate("window.__art.audioState()"); res['hint_after'] = pg.is_visible('#audiohint')
    res['ok'] = res['hint_visible'] and a2['t'] > a1['t'] and not a2['paused'] and a2['graph'] and not res['hint_after']
    b.close()
res['console'] = cons
print(json.dumps(res, ensure_ascii=False, indent=1))
