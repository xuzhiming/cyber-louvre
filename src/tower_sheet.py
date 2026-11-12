"""renders/tower_open_before_after.png: plan cuts (NW + SW tower, 1F; 2F/3F identical) + interior views per storey, before/after."""
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager
from PIL import Image
fp = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not os.path.exists(fp): fp = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
font_manager.fontManager.addfont(fp); plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
B = json.load(open('/tmp/plan_before.json')); A = json.load(open('/tmp/plan_after.json'))
R = '/workspace/outputs/cyber_louvre/renders/'
fig = plt.figure(figsize=(16, 11.5), dpi=110)
regions = [('NW 塔楼 (西北) · 1F', (-92, 12, -36, 62)), ('SW 塔楼 (西南) · 1F', (-92, -62, -46, -12))]
LBL = {'HALL': '塔楼大厅', 'LOB': '电梯厅', 'CAB': '电梯', 'SHAFT': '楼梯间'}
for row, (title, (x0, y0, x1, y1)) in enumerate(regions):
    for col, (D, tag) in enumerate(((B, '拆除前'), (A, '拆除后'))):
        ax = fig.add_axes([0.02 + col * 0.5, 0.49 - row * 0.47, 0.46, 0.42])
        for k, s in D['spaces'].items():
            r = s['rect']
            if r[2] < x0 or r[0] > x1 or r[3] < y0 or r[1] > y1 or s['kind'] in ('outdoor',): continue
            fc = {'stair': '#ffe7b3', 'elevator': '#d6d6ff', 'pavilion_hall': '#e9f6ea', 'core_lobby': '#e9f6ea', 'corridor': '#f2f2f2', 'gallery': '#f8f1e7', 'hall': '#f2f2f2'}.get(s['kind'], '#fafafa')
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=fc, ec='none', zorder=0))
            nm = k.replace('_L1', ''); nm = next((v for kk, v in LBL.items() if '_' + kk in nm), nm.split('_', 1)[-1] if nm.startswith('PAV') else nm)
            ax.text((max(r[0], x0) + min(r[2], x1)) / 2, (max(r[1], y0) + min(r[3], y1)) / 2, nm, ha='center', va='center', fontsize=7, color='#555', zorder=5)
        for f in D['stairs']:
            for (a, b, c, d) in f: ax.add_patch(Rectangle((a, b), c - a, d - b, fc='#e0b060', ec='white', lw=0.2, zorder=1))
        for g, a, b, c, d in D['L1']:
            if c < x0 - 1 or a > x1 + 1 or d < y0 - 1 or b > y1 + 1: continue
            ax.add_patch(Rectangle((a, b), c - a, d - b, fc='#333' if g == 'Walls_Exterior' else '#7a6a8a', ec='none', zorder=3))
        if col == 1:
            for o in D['removed']:
                if o['axis'] == 'x': xs, ys = [o['coord']] * 2, [o['a0'], o['a1']]
                else: xs, ys = [o['a0'], o['a1']], [o['coord']] * 2
                if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1: continue
                ax.plot(xs, ys, color='#e0303a', lw=2.2, ls=(0, (3, 2)), zorder=4)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title('%s — %s' % (title, tag) + ('（红色虚线 = 已拆除的墙）' if col else ''), fontsize=12)
fig.text(0.02, 0.965, '塔楼内部墙 + 相邻房间围墙拆除（t27u）· 平面剖切 z = 楼面 +1.0 m（2F / 3F 布局与 1F 相同）· 深灰 = 外墙（保留）· 紫灰 = 内墙 · 橙 = 楼梯（保留）· 蓝 = 电梯（保留）', fontsize=12)
fig.savefig('/tmp/plans.png')
from PIL import ImageDraw, ImageFont
F = ImageFont.truetype(fp, 26); FB = ImageFont.truetype(fp, 34)
views = [('NW_hall_to_rooms', 'L1', '1F · NW 塔楼大厅 → 相邻房间'), ('NW_hall_to_lobby', 'L1', '1F · NW 塔楼大厅 → 电梯厅'), ('SW_hall_to_rooms', 'L1', '1F · SW 塔楼大厅 → 相邻房间'),
         ('NW_hall_to_rooms', 'L2', '2F · NW 塔楼大厅 → 相邻房间'), ('NW_hall_to_lobby', 'L2', '2F · NW 塔楼大厅 → 电梯厅'),
         ('NW_hall_to_rooms', 'L3', '3F · NW 塔楼大厅 → 相邻房间'), ('NW_hall_to_lobby', 'L3', '3F · NW 塔楼大厅 → 电梯厅')]
TW = 860; tiles = []
for v, lv, t in views:
    row = []
    for tag in ('before', 'after'):
        im = Image.open(R + 'tower/%s_%s_%s.png' % (v, lv, tag)).convert('RGB'); w, h = im.size; im = im.crop((0, int(h * 0.15), w, h)); im = im.resize((TW, int(TW * im.height / im.width)))
        c = Image.new('RGB', (TW, im.height + 44), (18, 16, 26)); c.paste(im, (0, 44)); ImageDraw.Draw(c).text((10, 6), t + ' — ' + ('拆除前' if tag == 'before' else '拆除后'), fill=(255, 225, 140), font=F); row.append(c)
    tiles.append(row)
P = Image.open('/tmp/plans.png').convert('RGB'); P = P.resize((2 * TW + 30, int((2 * TW + 30) * P.height / P.width)))
H = P.height + sum(r[0].height + 16 for r in tiles) + 40
S = Image.new('RGB', (2 * TW + 30, H), (255, 255, 255)); S.paste(P, (0, 0)); y = P.height + 20
dk = Image.new('RGB', (2 * TW + 30, H - P.height), (10, 10, 16)); S.paste(dk, (0, P.height))
for r in tiles:
    S.paste(r[0], (0, y)); S.paste(r[1], (TW + 30, y)); y += r[0].height + 16
S.save(R + 'tower_open_before_after.png'); print('saved', S.size)
