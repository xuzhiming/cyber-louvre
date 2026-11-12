"""Interior props (visual only, not part of the walk-BVH): ceiling lights, exhibits, hologram, door frames."""
import math, random
import numpy as np
import spec
from spec import SPACES, DOORS, BAND_Z, SLAB


FIXTURES = []     # every light/emissive fixture: dict(space, bbox=(x0,y0,z0,x1,y1,z1), mat, kind) -> checked by verify.py
FIX_MARGIN = 0.5  # fixtures stop at least this far from stair openings, doorways and space ends

def stair_voids(zc, inflate=FIX_MARGIN):
    """plan rects (inflated) of everything a ceiling fixture at height zc must stay away from: stair treads that rise to within
    2.4 m of it, the openings (holes) cut in slabs, landings."""
    out = []
    for st in spec.STAIRS:
        for f in st['flights']:
            for i in range(1, f['n'] + 1):
                r, zt = spec.flight_step_rect(f, i)
                if zt > zc - 2.4 - 0.3 and zt < zc + 3.0:
                    out.append((r[0] - inflate, r[1] - inflate, r[2] + inflate, r[3] + inflate))
        for r, z in st['landings']:
            if z > zc - 2.7 and z < zc + 3.0: out.append((r[0] - inflate, r[1] - inflate, r[2] + inflate, r[3] + inflate))
    for z, rs in spec.HOLES.items():
        if abs(z - (zc + 0.05 + SLAB)) < 0.6:
            out += [(r[0] - inflate, r[1] - inflate, r[2] + inflate, r[3] + inflate) for r in rs]
    return out

def door_voids(sp, inflate=FIX_MARGIN):
    out = []
    for d in DOORS:
        if sp['id'] not in (d['a'], d['b']) or d['glass']: continue
        w = d['width'] / 2
        if d['axis'] == 'x': out.append((d['coord'] - 0.3 - inflate, d['center'] - w - inflate, d['coord'] + 0.3 + inflate, d['center'] + w + inflate))
        else: out.append((d['center'] - w - inflate, d['coord'] - 0.3 - inflate, d['center'] + w + inflate, d['coord'] + 0.3 + inflate))
    return out

def _hit(a, b):
    # a = (x0,y0,z0,x1,y1,z1) fixture bbox, b = (x0,y0,x1,y1) plan rect
    return a[0] < b[2] and a[3] > b[0] and a[1] < b[3] and a[4] > b[1]

def ceiling_fixtures(sp, zc):
    """Segmented ceiling light panels (3 m x 0.7 m) along the long axis, fully inside the space, never over stair mouths / doorways."""
    x0, y0, x1, y1 = sp['rect']; lx, ly = x1 - x0, y1 - y0
    voids = stair_voids(zc) + door_voids(sp)
    along_x = lx >= ly
    a0, a1 = (x0, x1) if along_x else (y0, y1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    seg, gap, inset = 3.0, 1.2, 1.0 + 0.2     # inset from the space ends (+ half wall thickness)
    L = (a1 - a0) - 2 * inset
    if L < seg: return []
    n = int((L + gap) // (seg + gap)); n = max(n, 1)
    tot = n * seg + (n - 1) * gap; s = a0 + ((a1 - a0) - tot) / 2
    res = []
    for k in range(n):
        p0 = s + k * (seg + gap); p1 = p0 + seg
        bb = (p0, cy - 0.35, zc, p1, cy + 0.35, zc + 0.06) if along_x else (cx - 0.35, p0, zc, cx + 0.35, p1, zc + 0.06)
        if any(_hit(bb, v) for v in voids): continue
        res.append(bb)
    return res

def props(acc, seed=5):
    FIXTURES.clear()
    rng = random.Random(seed)
    G = 'Props'
    ex_mats = ['exhibit_a', 'exhibit_b', 'exhibit_c', 'exhibit_d']
    for sp in SPACES.values():
        if not sp['walls'] or sp['kind'] in ('elevator', 'stair'): continue
        x0, y0, x1, y1 = sp['rect']; z0, z1 = sp['z0'], sp['z1']
        if sp['level'] == 'B1': z1 = 0.0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lx, ly = x1 - x0, y1 - y0
        zc = z1 - SLAB - 0.05 if sp['kind'] not in ('lobby', 'atrium') else None
        if zc is not None:
            for bb in ceiling_fixtures(sp, zc):
                acc.box(G, 'light_panel', bb[0], bb[1], bb[2], bb[3], bb[4], bb[5])
                FIXTURES.append(dict(space=sp['id'], bbox=bb, mat='light_panel', kind='ceiling_panel'))
        if sp['kind'] in ('gallery', 'hall', 'pavilion_hall'):
            n = 3 if sp['kind'] == 'gallery' else 6
            for k in range(n):
                if lx >= ly:
                    px = x0 + lx * (k + 0.5) / n; py = cy + (ly * 0.28) * (1 if k % 2 else -1)
                else:
                    py = y0 + ly * (k + 0.5) / n; px = cx + (lx * 0.28) * (1 if k % 2 else -1)
                acc.box(G, 'stone_trim_in', px - 0.5, py - 0.5, z0, px + 0.5, py + 0.5, z0 + 1.1)
                m = ex_mats[rng.randrange(4)]
                acc.box(G, m, px - 0.3, py - 0.3, z0 + 1.1, px + 0.3, py + 0.3, z0 + 1.7)
            # wall art on the far wall
            if lx >= ly:
                acc.box(G, 'exhibit_art', cx - 1.2, y1 - 0.45, z0 + 2.3, cx + 1.2, y1 - 0.35, z0 + 3.9)
            else:
                acc.box(G, 'exhibit_art', x1 - 0.45, cy - 1.2, z0 + 2.3, x1 - 0.35, cy + 1.2, z0 + 3.9)
        if sp['kind'] == 'mech':
            acc.box(G, 'frame_dark', x0 + 1, y0 + 1, z0, x0 + 3, y0 + 3.5, z0 + 2.2)
            acc.box(G, 'window_cyan', x0 + 1.2, y0 + 3.5, z0 + 1.0, x0 + 2.8, y0 + 3.55, z0 + 1.8)
            FIXTURES.append(dict(space=sp['id'], bbox=(x0 + 1.2, y0 + 3.5, z0 + 1.0, x0 + 2.8, y0 + 3.55, z0 + 1.8), mat='window_cyan', kind='mech_glow'))
    # hologram in the atrium
    cx, cy = 0.0, 46.0
    def ring(r, z, w, mat, n=48, grp='Hologram'):
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            acc.bar(grp, mat, (cx + r * math.cos(a0), cy + r * math.sin(a0), z), (cx + r * math.cos(a1), cy + r * math.sin(a1), z), w, w)
    ring(7.0, 11.5, 0.45, 'holo_purple'); ring(6.2, 11.5, 0.2, 'holo_cyan'); ring(5.0, 12.4, 0.25, 'holo_purple')
    ring(9.0, 0.06, 0.15, 'neon_purple'); ring(3.2, 0.06, 0.2, 'neon_cyan')
    acc.cyl('Hologram', 'holo_cyan', cx, cy, 0.5, 11.5, 0.45, n=14, r1=0.35)
    acc.cyl('Hologram', 'holo_cyan', cx, cy, 11.5, 22.0, 0.35, n=14, r1=0.12)
    acc.cyl('Hologram', 'stone_trim_in', cx, cy, 0.0, 0.5, 2.4, n=24)
    acc.cyl('Hologram', 'holo_purple', cx, cy, 11.2, 11.8, 2.0, n=24)
    # lobby: glowing floor medallion + chandelier rings
    acc.cyl(G, 'neon_purple', 0, 20, 0.0, 0.03, 1.0, n=3, r1=1.0) if False else None
    # door frames (visual)
    for d in DOORS:
        if d['glass']: continue
        zb0 = BAND_Z[d['band']][0]
        w, h, c, co = d['width'], d['height'], d['center'], d['coord']
        if d['axis'] == 'x':
            for s in (-1, 1):
                acc.box(G, 'gold' if d['width'] > 2.0 else 'frame_dark', co - 0.3, c + s * (w / 2) - 0.07, zb0, co + 0.3, c + s * (w / 2) + 0.07, zb0 + h)
            acc.box(G, 'gold' if d['width'] > 2.0 else 'frame_dark', co - 0.3, c - w / 2, zb0 + h - 0.1, co + 0.3, c + w / 2, zb0 + h + 0.1)
        else:
            for s in (-1, 1):
                acc.box(G, 'gold' if d['width'] > 2.0 else 'frame_dark', c + s * (w / 2) - 0.07, co - 0.3, zb0, c + s * (w / 2) + 0.07, co + 0.3, zb0 + h)
            acc.box(G, 'gold' if d['width'] > 2.0 else 'frame_dark', c - w / 2, co - 0.3, zb0 + h - 0.1, c + w / 2, co + 0.3, zb0 + h + 0.1)
