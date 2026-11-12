import time, sys
from playwright.sync_api import sync_playwright
ROOT='/workspace/outputs/cyber_louvre/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg=b.new_page(viewport={'width':480,'height':270})
    pg.goto('file://'+ROOT+'web/preview.html'); pg.wait_for_function('window.__collisionReady===true',timeout=120000)
    pg.keyboard.press('KeyF'); time.sleep(1)
    pg.evaluate('window.__walk.setPos(0,-56,0)'); pg.evaluate('window.__walk.setLook(Math.PI,0)'); 
    pg.evaluate('window.__walk.setLook(0,0)')
    pg.keyboard.down('KeyW'); t0=time.time()
    while time.time()-t0<14:
        s=pg.evaluate('window.__walk.state()'); print(round(s['x'],2),round(s['y'],2),round(s['z'],3),s['grounded']); time.sleep(0.7)
    b.close()
