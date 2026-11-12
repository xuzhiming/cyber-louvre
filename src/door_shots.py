import time, math
from playwright.sync_api import sync_playwright
ROOT='/workspace/outputs/cyber_louvre/'; SH=ROOT+'renders/walk/'
# name, door id, standing pos closed (x,y), standing pos open (x,y), look target (x,y,z)
S=[('lobby','LOBBY',(0,-3),(0,4.0),(0,8,2.0)),('pyramid_main','PYR_MAIN',(0,-69.6),(0,-66.8),(0,-60,1.2)),
   ('pyramid_smallL','PYR_SL',(-37,-64.5),(-37,-59.5),(-37,-54,1.0)),('pyramid_smallR','PYR_SR',(37,-64.5),(37,-59.5),(37,-54,1.0))]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg=b.new_page(viewport={'width':1280,'height':720}); errs=[]
    pg.on('pageerror',lambda e: errs.append(str(e))); pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
    pg.goto('file://'+ROOT+'web/preview.html'); pg.wait_for_function('window.__collisionReady===true',timeout=120000)
    pg.keyboard.press('KeyF'); time.sleep(1); pg.keyboard.press('KeyH')
    for n,did,pc,po,tg in S:
        for tag,pos in (('closed',pc),('open',po)):
            # far start so the door state is definitely closed, then place
            pg.evaluate('window.__walk.setPos(0,-30,0)'); time.sleep(1.5)
            pg.evaluate(f'window.__walk.setPos({pos[0]},{pos[1]},0)')
            yaw=math.atan2(-(tg[0]-pos[0]),tg[1]-pos[1]); dist=math.hypot(tg[0]-pos[0],tg[1]-pos[1])
            pg.evaluate(f'window.__walk.setLook({yaw},{math.atan2(tg[2]-1.7,dist)})')
            time.sleep(6.0 if tag=='open' else 0.3)
            o={d["id"]:d["open"] for d in pg.evaluate("window.__doors()")}[did]
            # closed shot: door must still be shut (we were >4.5 m away only if pos is far enough)
            pg.screenshot(path=SH+f'door_{n}_{tag}.png'); print(n,tag,'door open amount',o)
    print(errs); b.close()
