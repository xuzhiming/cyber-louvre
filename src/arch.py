"""Structural architecture: walls with real door cut-outs, slabs with stair holes, stairs, platform rails."""
import math
import spec
from spec import *
from geom import Acc, rect_minus

T_EXT, T_INT = 0.8, 0.4
ARCH_GROUPS = ['Walls_Exterior', 'Walls_Interior', 'Slabs', 'Stairs']   # included in walk BVH

def _inside(r, x, y, eps=1e-6):
    return r[0] + eps < x < r[2] - eps and r[1] + eps < y < r[3] - eps

_WINS = []
WINDOW_CUTS = []   # openings actually cut through exterior walls (filled by build_walls)
def _windows():
    if not _WINS:
        import exterior
        _WINS.extend(exterior.collect_windows())
    return _WINS

def build_walls(acc, report=None):
    raw = {}
    for sp in SPACES.values():
        if not sp['walls']: continue
        x0, y0, x1, y1 = sp['rect']
        for band in sp['bands']:
            zb0, zb1 = BAND_Z[band]
            top = min(sp['z1'], zb1)
            for axis, coord, a0, a1 in (('y', y0, x0, x1), ('y', y1, x0, x1), ('x', x0, y0, y1), ('x', x1, y0, y1)):
                raw.setdefault((axis, round(coord, 3), band), []).append((a0, a1, top, sp['id']))
    wall_spaces = {b: [s for s in SPACES.values() if s['walls'] and b in s['bands']] for b in ORDER}
    segs = []   # (axis, coord, a0, a1, band, top, ext, out_sign)
    for (axis, coord, band), edges in raw.items():
        bps = sorted(set([e[0] for e in edges] + [e[1] for e in edges]))
        opens = [o for o in OPENS if o['axis'] == axis and abs(o['coord'] - coord) < 1e-3 and band in o['bands']]
        elem = []
        for p, q in zip(bps[:-1], bps[1:]):
            if q - p < 1e-4: continue
            cov = [e for e in edges if e[0] <= p + 1e-6 and e[1] >= q - 1e-6]
            if not cov: continue
            mid = (p + q) / 2
            # open?
            if any(o['a0'] <= p + 1e-6 and o['a1'] >= q - 1e-6 for o in opens): continue
            top = max(e[2] for e in cov)
            pr = []
            for sgn in (-1, 1):
                if axis == 'y': px, py = mid, coord + sgn * 0.5
                else: px, py = coord + sgn * 0.5, mid
                pr.append(any(_inside(s['rect'], px, py) for s in wall_spaces[band]))
            if band == 'B1': ext, out = False, 1
            elif pr[0] and pr[1]: ext, out = False, 1
            else: ext, out = True, (-1 if not pr[0] else 1)
            elem.append([p, q, top, ext, out])
        # merge
        merged = []
        for e in elem:
            if merged and abs(merged[-1][1] - e[0]) < 1e-6 and merged[-1][2] == e[2] and merged[-1][3] == e[3] and merged[-1][4] == e[4]:
                merged[-1][1] = e[1]
            else: merged.append(list(e))
        for p, q, top, ext, out in merged:
            segs.append((axis, coord, p, q, band, top, ext, out))
    n_cut = 0; n_win = 0; WINDOW_CUTS.clear()
    for axis, coord, p, q, band, top, ext, out in segs:
        t = T_EXT if ext else T_INT
        zb0, zb1 = BAND_Z[band]
        zlo = zb0 - SLAB
        doors = [d for d in DOORS if d['axis'] == axis and abs(d['coord'] - coord) < 1e-3 and d['band'] == band and not d['glass']
                 and d['center'] - d['width'] / 2 < q and d['center'] + d['width'] / 2 > p]
        doors.sort(key=lambda d: d['center'])
        group = 'Walls_Exterior' if ext else 'Walls_Interior'
        mat = 'stone_wall' if ext else ('concrete' if band == 'B1' else 'plaster')
        pieces = []
        cur = p
        for d in doors:
            d0, d1 = d['center'] - d['width'] / 2, d['center'] + d['width'] / 2
            d0, d1 = max(d0, p), min(d1, q)
            if d0 > cur + 1e-4: pieces.append((cur, d0, zlo, top))
            pieces.append((d0, d1, zb0 + d['height'], top))   # lintel
            cur = d1; n_cut += 1
        if q > cur + 1e-4: pieces.append((cur, q, zlo, top))
        # window openings (exterior walls only; the glass pane sits in the outer face, see exterior.facades)
        if ext:
            wl = [w for w in _windows() if w['axis'] == axis and abs(w['coord'] - coord) < 1e-3 and w['band'] == band and w['out'] == out
                  and w['a0'] < q - 1e-6 and w['a1'] > p + 1e-6]
            for w in wl:
                npcs = []
                for (a0, a1, z0, z1) in pieces:
                    wa0, wa1 = max(w['a0'], a0), min(w['a1'], a1)
                    wz0, wz1 = max(w['z0'], z0), min(w['z1'], z1)
                    if wa1 - wa0 < 1e-4 or wz1 - wz0 < 1e-4:
                        npcs.append((a0, a1, z0, z1)); continue
                    n_win += 1; WINDOW_CUTS.append(dict(axis=axis, coord=coord, a0=wa0, a1=wa1, z0=wz0, z1=wz1, out=out, band=band))
                    for pc in ((a0, wa0, z0, z1), (wa1, a1, z0, z1), (wa0, wa1, z0, wz0), (wa0, wa1, wz1, z1)):
                        if pc[1] - pc[0] > 1e-4 and pc[3] - pc[2] > 1e-4: npcs.append(pc)
                pieces = npcs
        for a0, a1, z0, z1 in pieces:
            if z1 - z0 < 1e-3: continue
            e0 = a0 - (t / 2 if a0 <= p + 1e-6 else 0)
            e1 = a1 + (t / 2 if a1 >= q - 1e-6 else 0)
            if axis == 'y': acc.box(group, mat, e0, coord - t / 2, z0, e1, coord + t / 2, z1)
            else: acc.box(group, mat, coord - t / 2, e0, z0, coord + t / 2, e1, z1)
    if report is not None: report['door_cuts'] = n_cut; report['window_cuts'] = n_win; report['wall_segments'] = len(segs)

def build_slabs(acc):
    done = set()
    def slab(rect, z, group, mat):
        key = (round(z, 3), tuple(round(v, 3) for v in rect))
        if key in done: return
        done.add(key)
        holes = HOLES.get(round(z, 3), HOLES.get(z, []))
        for r in rect_minus(rect, holes):
            if r[2] - r[0] > 1e-3 and r[3] - r[1] > 1e-3:
                acc.rect(group, mat, r, z - SLAB, z)
    for sp in SPACES.values():
        for r in sp['floor']:
            if sp['kind'] == 'outdoor': slab(r, sp['z0'], 'Ground', 'plaza')
            elif sp['level'] == 'B1': slab(r, sp['z0'], 'Slabs', 'concrete')
            else: slab(r, sp['z0'], 'Slabs', 'slab')
        if sp['ceil'] and sp['walls']:
            slab(sp['rect'], sp['z1'], 'Slabs', 'slab')

def build_stairs(acc):
    for st in STAIRS:
        for f in st['flights']:
            for i in range(1, f['n'] + 1):
                r, zt = flight_step_rect(f, i)
                acc.rect('Stairs', 'stair', r, zt - abs(f['riser']) - 0.3, zt)
            # handrails (outer sides) as slanted bars
            ex = flight_end(f)
            for sgn in (-1, 1):
                if abs(f['dx']) > 0.5:
                    off = (0, sgn * (f['w'] / 2 - 0.05))
                else:
                    off = (sgn * (f['w'] / 2 - 0.05), 0)
                p0 = (f['x'] + off[0], f['y'] + off[1], f['z0'] + 1.0)
                p1 = (ex[0] + off[0], ex[1] + off[1], ex[2] + 1.0)
                acc.bar('Rails', 'rail_metal', p0, p1, 0.07, 0.07)
        for r, z in st['landings']:
            acc.rect('Slabs', 'slab', r, z - SLAB, z)

def build_rails(acc):
    plats = [s for s in SPACES.values() if s['kind'] == 'platform']
    pts = []
    for st in STAIRS:
        for f in st['flights']:
            pts.append((f['x'], f['y'], f['z0'], f['w'], f))
            e = flight_end(f); pts.append((e[0], e[1], e[2], f['w'], f))
    for p in plats:
        x0, y0, x1, y1 = p['rect']; z = p['z0']
        for axis, coord, a0, a1 in (('y', y0, x0, x1), ('y', y1, x0, x1), ('x', x0, y0, y1), ('x', x1, y0, y1)):
            iv = [(a0, a1)]
            def sub(iv, c0, c1):
                out = []
                for u, v in iv:
                    if c1 <= u or c0 >= v: out.append((u, v))
                    else:
                        if c0 > u: out.append((u, c0))
                        if c1 < v: out.append((c1, v))
                return out
            # wall lines
            if axis == 'x' and abs(abs(coord) - 14) < 1e-6: continue
            if axis == 'y' and abs(coord - 60) < 1e-6: continue
            # neighbouring platforms (same z) touching this edge
            for o in plats:
                if o is p or abs(o['z0'] - z) > 0.01: continue
                ox0, oy0, ox1, oy1 = o['rect']
                if axis == 'y':
                    for oc in (oy0, oy1):
                        if abs(oc - coord) < 1e-6 and ox0 < a1 and ox1 > a0 and (o['rect'][1] != o['rect'][3]):
                            # other lies on the opposite side if its edge at coord and extends away
                            if (oy0 == oc and oy1 > oc and coord == y1) or (oy1 == oc and oy0 < oc and coord == y0) or \
                               (oy0 == oc and coord == y1) or (oy1 == oc and coord == y0):
                                iv = sub(iv, ox0, ox1)
                else:
                    for oc in (ox0, ox1):
                        if abs(oc - coord) < 1e-6 and oy0 < a1 and oy1 > a0:
                            if (ox0 == oc and coord == x1) or (ox1 == oc and coord == x0):
                                iv = sub(iv, oy0, oy1)
            # stair gaps
            for (px, py, pz, w, f) in pts:
                if abs(pz - z) > 0.05: continue
                if axis == 'y' and abs(py - coord) < 0.45: iv = sub(iv, px - w / 2 - 0.15, px + w / 2 + 0.15)
                if axis == 'x' and abs(px - coord) < 0.45: iv = sub(iv, py - w / 2 - 0.15, py + w / 2 + 0.15)
            # edges where this platform overlaps others in x/y interior handled above
            for u, v in iv:
                if v - u < 0.2: continue
                if axis == 'y':
                    acc.box('Rails', 'rail_glass', u, coord - 0.03, z + 0.12, v, coord + 0.03, z + 1.05)
                    acc.box('Rails', 'rail_metal', u, coord - 0.06, z + 1.05, v, coord + 0.06, z + 1.15)
                else:
                    acc.box('Rails', 'rail_glass', coord - 0.03, u, z + 0.12, coord + 0.03, v, z + 1.05)
                    acc.box('Rails', 'rail_metal', coord - 0.06, u, z + 1.05, coord + 0.06, v, z + 1.15)

def _rail_run(acc, axis, coord, u, v, z):
    if v - u < 0.2: return
    if axis == 'y':
        acc.box('Rails', 'rail_glass', u, coord - 0.03, z + 0.12, v, coord + 0.03, z + 1.05)
        acc.box('Rails', 'rail_metal', u, coord - 0.06, z + 1.05, v, coord + 0.06, z + 1.15)
    else:
        acc.box('Rails', 'rail_glass', coord - 0.03, u, z + 0.12, coord + 0.03, v, z + 1.05)
        acc.box('Rails', 'rail_metal', coord - 0.06, u, z + 1.05, coord + 0.06, v, z + 1.15)

def _sub(iv, c0, c1):
    out = []
    for u, v in iv:
        if c1 <= u or c0 >= v: out.append((u, v))
        else:
            if c0 > u: out.append((u, c0))
            if c1 < v: out.append((c1, v))
    return out

def build_hole_rails(acc):
    """guardrail around every slab opening, open only on the side people step on/off the stair"""
    for m in HOLE_META:
        x0, y0, x1, y1 = m['rect']; z = m['z']
        for side, axis, coord, a0, a1 in (('S', 'y', y0, x0, x1), ('N', 'y', y1, x0, x1), ('W', 'x', x0, y0, y1), ('E', 'x', x1, y0, y1)):
            if side == m['access']: continue
            nrm = {'S': (0, -1), 'N': (0, 1), 'W': (-1, 0), 'E': (1, 0)}[side]
            floors = [r for sp in SPACES.values() if abs(sp['z0'] - z) < 0.01 and sp['kind'] != 'outdoor' for r in sp['floor']] + \
                     [r for sp in SPACES.values() if sp['kind'] == 'outdoor' and abs(sp['z0'] - z) < 0.01 for r in sp['floor']]
            n = max(1, int(round((a1 - a0) / 0.1))); run = None
            for i in range(n):
                t = a0 + (i + 0.5) * (a1 - a0) / n
                px, py = (t, coord) if axis == 'y' else (coord, t)
                qx, qy = px + nrm[0] * 0.15, py + nrm[1] * 0.15
                on = any(r[0] < qx < r[2] and r[1] < qy < r[3] for r in floors)
                if on and run is None: run = t - 0.05
                if (not on) and run is not None:
                    _rail_run(acc, axis, coord, run, t - 0.05, z); run = None
            if run is not None: _rail_run(acc, axis, coord, run, a1, z)

def build_landing_rails(acc):
    """balustrade on the free edges of every intermediate landing (not where a flight meets it, not at walls)"""
    for st in STAIRS:
        bounds_x, bounds_y = [], []
        for sid in (st['a'], st['b']):
            r = SPACES[sid]['rect']
            if SPACES[sid]['walls']: bounds_x += [r[0], r[2]]; bounds_y += [r[1], r[3]]
        pts = []
        for f in st['flights']:
            pts.append((f['x'], f['y'], f['z0'], f['w']))
            e = flight_end(f); pts.append((e[0], e[1], e[2], f['w']))
        for r, z in st['landings']:
            x0, y0, x1, y1 = r
            for axis, coord, a0, a1 in (('y', y0, x0, x1), ('y', y1, x0, x1), ('x', x0, y0, y1), ('x', x1, y0, y1)):
                if any(abs(coord - b) < 0.5 for b in (bounds_y if axis == 'y' else bounds_x)): continue
                iv = [(a0, a1)]
                for (px, py, pz, w) in pts:
                    if abs(pz - z) > 0.05: continue
                    if axis == 'y' and abs(py - coord) < 0.05: iv = _sub(iv, px - w / 2 - 0.1, px + w / 2 + 0.1)
                    if axis == 'x' and abs(px - coord) < 0.05: iv = _sub(iv, py - w / 2 - 0.1, py + w / 2 + 0.1)
                for u, v in iv: _rail_run(acc, axis, coord, u, v, z)

def build_shaft_rails(acc):
    """pavilion stair shafts: the open well between the two legs is guarded at every arrival strip"""
    for sp in SPACES.values():
        if sp['kind'] != 'stair': continue
        x0, y0, x1, y1 = sp['rect']; z = sp['z0']
        for (sx0, sy0, sx1, sy1) in sp['floor']:
            for axis, coord, a0, a1 in (('y', sy0, sx0, sx1), ('y', sy1, sx0, sx1)):
                if abs(coord - y0) < 0.01 or abs(coord - y1) < 0.01: continue
                iv = [(a0, a1)]
                for st in STAIRS:
                    for f in st['flights']:
                        for (px, py, pz) in ((f['x'], f['y'], f['z0']), flight_end(f)):
                            if abs(pz - z) < 0.05 and abs(py - coord) < 0.05: iv = _sub(iv, px - f['w'] / 2 - 0.1, px + f['w'] / 2 + 0.1)
                for u, v in iv: _rail_run(acc, axis, coord, u, v, z)

def build_arch(acc, report=None):
    spec.build()
    build_walls(acc, report); build_slabs(acc); build_stairs(acc); build_rails(acc)
    build_hole_rails(acc); build_landing_rails(acc); build_shaft_rails(acc)

if __name__ == '__main__':
    a = Acc(); rep = {}
    build_arch(a, rep)
    print(rep, a.tri_by_group(), a.stats())
