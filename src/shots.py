import time
from playwright.sync_api import sync_playwright
ROOT='/workspace/outputs/cyber_louvre/'; SH=ROOT+'renders/walk/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg=b.new_page(viewport={'width':1280,'height':720}); errs=[]
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.goto('file://'+ROOT+'web/preview.html'); pg.wait_for_function('window.__collisionReady===true',timeout=120000)
    pg.click('#walkBtn'); time.sleep(1.5); pg.screenshot(path=SH+'hd_01_plaza.png')
    for k,n in [('Digit2','lobby'),('Digit4','f2'),('Digit6','pav'),('Digit7','b1')]:
        pg.keyboard.press(k); time.sleep(1.5); pg.screenshot(path=SH+f'hd_02_{n}.png')
    pg.keyboard.press('KeyH'); time.sleep(0.5); pg.screenshot(path=SH+'hd_03_help_hidden.png')
    print(errs); b.close()
