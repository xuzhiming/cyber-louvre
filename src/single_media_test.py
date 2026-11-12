"""Single-media playback test (t35u).  Stand between two videos and face each in turn: the faced one plays (with sound after a
gesture), the other pauses (last frame kept); at most one element un-paused at any sampled moment; audio work vs neighbouring
video mutually exclusive; tab hidden pauses all.  usage: single_media_test.py URL [TAG]"""
import sys, time, json, math
from playwright.sync_api import sync_playwright
url = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else 'local'
R = '/workspace/outputs/cyber_louvre/renders/art/'
S = {s['id']: s for s in json.load(open('/workspace/outputs/cyber_louvre/web/slots.json'))['slots']}
def stand(a, b, off):
    A, B = S[a], S[b]; mx, my = (A['pos'][0] + B['pos'][0]) / 2, (A['pos'][1] + B['pos'][1]) / 2
    nx, ny = A['normal'][:2]; return mx + nx * off, my + ny * off, A['pos'][2] - 1.6 if False else round(A['pos'][2] - 1.6 + 0.0, 2)
def yaw_to(p, sid):
    x, y = S[sid]['pos'][:2]; return math.atan2(-(x - p[0]), y - p[1])
res, cons = {}, []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1100, 'height': 640})
    pg.on('console', lambda m: cons.append((m.type, m.text[:200])) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: cons.append(('pageerror', str(e)[:200])))
    pg.goto(url); pg.wait_for_function('window.__ready === true', timeout=240000); pg.wait_for_function('window.__collisionReady === true', timeout=240000)
    M = lambda: pg.evaluate('window.__art.media()')
    floor_of = lambda sid: {'L1': 0, 'L2': 8, 'L3': 16}[S[sid]['band']]
    def face(a, b, target, off=3.0):
        P = stand(a, b, off); pg.evaluate(f"window.__walk.place({P[0]}, {P[1]}, {floor_of(a)}, {yaw_to(P, target)})"); return P
    def watch(secs, want=None):
        mx, hist = 0, []
        t0 = time.time()
        while time.time() - t0 < secs:
            m = M(); mx = max(mx, m['unpaused']); hist.append((round(time.time() - t0, 1), m['cur'], m['unpaused']))
            if want and m['cur'] == want and m['unpaused'] == 1 and any(e['slot'] == want and not e['paused'] and e['t'] > 0.3 for e in m['els']) and time.time() - t0 > 2: break
            time.sleep(0.1)
        return mx, hist[-3:]
    pg.evaluate("window.__walk.enter()")
    A, B = 'S048', 'S049'
    face(A, B, A); mx0, h0 = watch(20, A)
    res['1_face_A_before_gesture'] = {'media': M(), 'max_unpaused': mx0, 'hint_visible': pg.is_visible('#audiohint')}
    pg.screenshot(path=R + f'single_{tag}_A_muted.png')
    pg.mouse.click(550, 320); time.sleep(0.5); face(A, B, A)
    m1 = M(); time.sleep(2.0); m2 = M()
    ea1 = next(e for e in m1['els'] if e['slot'] == A); ea2 = next(e for e in m2['els'] if e['slot'] == A)
    res['2_after_gesture'] = {'A': ea2, 'advancing': ea2['t'] > ea1['t'], 'unmuted': not ea2['muted'] and ea2['elVol'] > 0, 'hint_visible': pg.is_visible('#audiohint')}
    pg.screenshot(path=R + f'single_{tag}_A.png')
    face(A, B, B); mxB, hB = watch(25, B); mB = M()
    eb = next((e for e in mB['els'] if e['slot'] == B), None); ea = next((e for e in mB['els'] if e['slot'] == A), None)
    res['3_face_B'] = {'cur': mB['cur'], 'B': eb, 'A_after': ea, 'max_unpaused': mxB, 'last': hB, 'A_last_frame_kept': pg.evaluate(f"window.__art.slot('{A}').kind")}
    pg.screenshot(path=R + f'single_{tag}_B.png')
    face(A, B, A); mxA2, hA2 = watch(25, A); res['4_back_to_A'] = {'cur': M()['cur'], 'max_unpaused': mxA2}
    # audio work S129 vs neighbouring video S128 (same wall, 2F)
    AU, V = 'S129', 'S128'
    face(V, AU, AU); mx5, _ = watch(25, AU); m5 = M()
    res['5_face_audio'] = {'cur': m5['cur'], 'max_unpaused': mx5, 'els': m5['els'], 'audio': pg.evaluate(f"window.__art.audio('{AU}')")}
    pg.screenshot(path=R + f'single_{tag}_audio.png')
    face(V, AU, V); mx6, _ = watch(25, V); m6 = M()
    res['6_face_video_next_to_audio'] = {'cur': m6['cur'], 'max_unpaused': mx6, 'els': m6['els']}
    # look away (nothing in the cone) -> everything pauses after the fade
    P = stand(V, AU, 3.0); pg.evaluate(f"window.__walk.place({P[0]}, {P[1]}, 8, {yaw_to(P, V) + math.pi})"); time.sleep(4)
    res['7_look_away'] = {'cur': M()['cur'], 'unpaused': M()['unpaused']}
    # tab hidden -> all paused, visible again -> resumes
    face(V, AU, V); watch(15, V)
    pg.evaluate("Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange'))"); time.sleep(1.0)
    res['8_hidden'] = {'unpaused': M()['unpaused']}
    pg.evaluate("Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange'))"); time.sleep(3.0)
    res['8_visible_again'] = {'unpaused': M()['unpaused'], 'cur': M()['cur']}
    res['switch_log'] = M()['log']
    res['art_state'] = pg.evaluate('window.__art.state()')
    b.close()
r = res
res['checks'] = {
    'muted_before_gesture': r['1_face_A_before_gesture']['media']['cur'] == 'S048' and all(e['muted'] for e in r['1_face_A_before_gesture']['media']['els'] if not e['paused']) and r['1_face_A_before_gesture']['hint_visible'],
    'sound_after_gesture': r['2_after_gesture']['unmuted'] and r['2_after_gesture']['advancing'] and not r['2_after_gesture']['hint_visible'],
    'switch_to_B': r['3_face_B']['cur'] == 'S049' and r['3_face_B']['B'] and not r['3_face_B']['B']['paused'] and (r['3_face_B']['A_after'] is None or r['3_face_B']['A_after']['paused']),
    'back_to_A': r['4_back_to_A']['cur'] == 'S048',
    'audio_vs_video': r['5_face_audio']['cur'] == 'S129' and r['6_face_video_next_to_audio']['cur'] == 'S128' and all(e['paused'] for e in r['6_face_video_next_to_audio']['els'] if e['slot'] == 'S129'),
    'max_one_unpaused': max(r['1_face_A_before_gesture']['max_unpaused'], r['3_face_B']['max_unpaused'], r['4_back_to_A']['max_unpaused'], r['5_face_audio']['max_unpaused'], r['6_face_video_next_to_audio']['max_unpaused']) <= 1,
    'look_away_pauses': r['7_look_away']['unpaused'] == 0,
    'hidden_pauses': r['8_hidden']['unpaused'] == 0 and r['8_visible_again']['unpaused'] == 1,
    'console_errors_0': not cons }
res['console'] = cons
print(json.dumps(res, ensure_ascii=False, indent=1))
