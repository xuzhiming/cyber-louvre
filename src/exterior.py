"""Exterior: facades, roofs, dome, pyramids, neon, screens, ground."""
import math, random
import numpy as np
from geom import Acc, rect_minus
import spec
from spec import MASSES, PYR_MAIN, PYR_SMALL, DOME, BAND_Z, DOORS, mirror_rect

T_EXT = 0.8
BAY = 3.6
WIN_MATS = ['window_pink', 'window_warm', 'window_purple', 'window_warm', 'window_pink']

def side_defs(r):
    x0, y0, x1, y1 = r
    # name, outward normal, axis coord, along-range, along-axis
    return [('S', (0, -1), y0, (x0, x1), 'x'), ('N', (0, 1), y1, (x0, x1), 'x'),
            ('W', (-1, 0), x0, (y0, y1), 'y'), ('E', (1, 0), x1, (y0, y1), 'y')]

class Side:
    def __init__(self, nrm, coord, axis):
        self.n, self.c, self.axis = nrm, coord, axis
    def P(self, u, off, z):
        d = self.c + (self.n[1] if self.axis == 'x' else self.n[0]) * (T_EXT / 2 + off)
        return (u, d, z) if self.axis == 'x' else (d, u, z)
    @property
    def hint(self):
        return (self.n[0], self.n[1], 0.0)
    def box(self, acc, group, mat, u0, u1, o0, o1, z0, z1):
        a = self.P(u0, o0, z0); b = self.P(u1, o1, z1)
        acc.box(group, mat, a[0], a[1], a[2], b[0], b[1], b[2])

def arch_poly(uc, z0, w, zspring, n=8):
    pts = [(uc - w / 2, z0), (uc + w / 2, z0), (uc + w / 2, zspring)]
    for k in range(1, n):
        a = math.pi * k / n
        pts.append((uc + w / 2 * math.cos(a), zspring + w / 2 * math.sin(a)))
    pts += [(uc - w / 2, zspring)]
    return pts

def visible(mass, side_name, nrm, coord, ucenter, band):
    zt = BAND_Z[band][1]
    if mass['h'] < BAND_Z[band][0] + 0.5: return False
    ztop_band = min(zt, mass['h'])
    ax = ucenter
    for m in MASSES:
        if m is mass: continue
        r = m['rect']
        if side_name in ('S', 'N'): px, py = ax, coord + nrm[1] * 0.7
        else: px, py = coord + nrm[0] * 0.7, ax
        if r[0] < px < r[2] and r[1] < py < r[3] and m['h'] >= ztop_band - 0.01:
            return False
    return True

GABLE_WIN = [(-6, 32.9), (6, 32.9), (0, 36.3)]
WIN_HALF = {'L1': 1.1, 'L2': 0.9, 'L3': 0.7, 'L4': 0.6}
SKIPPED = []   # bays where a window would be blocked (partition wall / neighbouring roof behind it) -> plain wall bay

def window_ok(mass, nrm, coord, axis, uc, band):
    """a window is only placed where it can be a real opening: no interior partition (or building junction) meets the
    wall within the window width, and no neighbouring wing / roof volume sits right in front of it."""
    zb0, zb1 = BAND_Z[band]; zm = (zb0 + zb1) / 2; hw = WIN_HALF[band]
    out = nrm[1] if axis == 'x' else nrm[0]
    sps = [sp for sp in spec.SPACES.values() if sp['walls'] and band in sp['bands']]
    def inside(u):   # point 0.5 m inside the wall at along-coordinate u
        px, py = (u, coord - out * 0.5) if axis == 'x' else (coord - out * 0.5, u)
        return any(sp['rect'][0] < px < sp['rect'][2] and sp['rect'][1] < py < sp['rect'][3] for sp in sps)
    bounds = []
    for sp in sps:
        x0, y0, x1, y1 = sp['rect']
        if axis == 'x' and abs((y1 if out > 0 else y0) - coord) < 1e-3: bounds += [x0, x1]
        if axis == 'y' and abs((x1 if out > 0 else x0) - coord) < 1e-3: bounds += [y0, y1]
    if any(abs(b - uc) < 0.35 for b in bounds): return False          # partition right behind the glass centre
    # neighbouring mass (its facade / wall) or a north-wing roof (runs 10 m into the pavilions) right in front of the window
    for m in MASSES:
        if m is mass: continue
        x0, y0, x1, y1 = m['rect']; foot = [((x0, y0, x1, y1), m['h'] + 0.01)]
        if m['kind'] == 'nwing':
            fx0, fx1 = (x0 - 10, x1) if (x0 + x1) / 2 < 0 else (x0, x1 + 10)
            foot.append(((fx0, 40.0 - 10.2, fx1, 40.0 + 10.2), 31.0))
        for (rx0, ry0, rx1, ry1), ztop in foot:
            if zb0 >= ztop: continue
            for k in range(9):
                du = -hw - 0.2 + (2 * hw + 0.4) * k / 8
                px, py = (uc + du, coord + out * 0.5) if axis == 'x' else (coord + out * 0.5, uc + du)
                if rx0 < px < rx1 and ry0 < py < ry1: return False
    return True
WINDOWS = []   # window openings (wall coordinates) -> arch.build_walls cuts them through exterior walls that have a room behind

def reg(S, name, nrm, coord, u0, u1, z0, z1, band, with_pane=True):
    if with_pane: pane(S.P((u0 + u1) / 2, 0.065, (z0 + z1) / 2), (nrm[0], nrm[1]), 0.065 + T_EXT + 0.5, 'facade_' + band)
    WINDOWS.append(dict(axis=('y' if S.axis == 'x' else 'x'), coord=coord, a0=u0, a1=u1, z0=z0, z1=z1, band=band, out=(nrm[1] if S.axis == 'x' else nrm[0])))

def collect_windows():
    import random as _r
    if not spec.SPACES: spec.build()
    WINDOWS.clear()
    facades(Acc(), _r.Random(3))
    return list(WINDOWS)

# ---------------------------------------------------------------- window plan (round "fewer, bigger windows")
ROOM_KINDS = ('gallery', 'core_lobby', 'corridor', 'stair')            # small rooms: ONE centred floor-to-ceiling window
HALL_KINDS = ('hall', 'pavilion_hall', 'lobby', 'atrium')     # halls: tall windows on every 2nd (long runs: 3rd) structural bay
PLAN = {}
PLAN_LOG = []

def _in_rect(r, x, y): return r[0] < x < r[2] and r[1] < y < r[3]

def _face_exterior(sp, band, axis, coord, out, u):
    """is the room face at along-coordinate u a real, visible facade (no room / other wing / north-wing roof outside)?"""
    zb0 = BAND_Z[band][0]
    po = (u, coord + out * 0.6) if axis == 'x' else (coord + out * 0.6, u)
    for s2 in spec.SPACES.values():
        if s2['kind'] == 'outdoor' or band not in s2['bands']: continue
        if _in_rect(s2['rect'], *po): return None
    for m in MASSES:
        for (nm, nrm, c, (a0, a1), ax) in side_defs(m['rect']):
            o = nrm[1] if ax == 'x' else nrm[0]
            if ax == axis and abs(c - coord) < 1e-3 and o == out and a0 - 1e-6 <= u <= a1 + 1e-6:
                if not visible(m, nm, nrm, coord, u, band): return None
                for m2 in MASSES:
                    if m2 is m: continue
                    x0, y0, x1, y1 = m2['rect']; foot = [((x0, y0, x1, y1), m2['h'] + 0.01)]
                    if m2['kind'] == 'nwing':
                        fx0, fx1 = (x0 - 10, x1) if (x0 + x1) / 2 < 0 else (x0, x1 + 10)
                        foot.append(((fx0, 40.0 - 10.2, fx1, 40.0 + 10.2), 31.0))
                    for r, zt in foot:
                        if zb0 < zt and _in_rect(r, *((u, coord + out * 0.5) if axis == 'x' else (coord + out * 0.5, u))): return None
                return (m, nm, nrm, a0, a1)
    return None

def _runs(sp, band):
    """exterior runs of every face of a room: list of (axis, coord, out, u0, u1, mass, side)"""
    x0, y0, x1, y1 = sp['rect']; res = []
    for axis, coord, out, a0, a1 in (('x', y0, -1, x0, x1), ('x', y1, 1, x0, x1), ('y', x0, -1, y0, y1), ('y', x1, 1, y0, y1)):
        n = max(2, int((a1 - a0) / 0.25)); cur = None
        for k in range(n + 1):
            u = a0 + 0.12 + (a1 - a0 - 0.24) * k / n
            f = _face_exterior(sp, band, axis, coord, out, u)
            key = None if f is None else (f[0]['name'], f[1])
            if cur and cur[5] == key and key is not None: cur[4] = u
            else:
                if cur and cur[5] is not None: res.append(tuple(cur))
                cur = [axis, coord, out, u, u, key, f]
        if cur and cur[5] is not None: res.append(tuple(cur))
    return [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in res if r[4] - r[3] > 2.0]

def _doors_clear(axis, coord, band, u0, u1):
    return not any(d['axis'] == ('y' if axis == 'x' else 'x') and abs(d['coord'] - coord) < 1e-3 and d['band'] == band
                   and d['center'] - d['width'] / 2 - 0.8 < u1 and d['center'] + d['width'] / 2 + 0.8 > u0 for d in DOORS)

def plan_windows():
    plan = {}; PLAN_LOG.clear()
    def add(key, w): plan.setdefault(key, []).append(w)
    for sp in spec.SPACES.values():
        if (not sp['walls'] and sp['kind'] != 'stair') or sp['kind'] not in ROOM_KINDS + HALL_KINDS: continue
        for band in sp['bands']:
            zb0, zb1 = BAND_Z[band]; ztop = min(sp['z1'], zb1)
            if ztop - zb0 < 3.0: continue
            runs = _runs(sp, band)
            if not runs: continue
            if sp['kind'] in ROOM_KINDS:
                r = max(runs, key=lambda r: r[4] - r[3])          # ONE window per room, on its longest facade run
                L = r[4] - r[3]; uc = (r[3] + r[4]) / 2
                w = min(max(0.5 * L, 1.8), 5.0, L - 1.2)
                u0, u1 = uc - w / 2, uc + w / 2
                if not _doors_clear(r[0], r[1], band, u0, u1): continue
                add(r[5], dict(u0=u0, u1=u1, z0=zb0 + 0.08, z1=ztop - 1.0, band=band, kind='room', space=sp['id']))
                PLAN_LOG.append((sp['id'], band, 'room', 1))
            else:
                n_hall = 0
                for r in runs:
                    m, nm, nrm, a0, a1 = r[6]
                    nb = max(1, round((a1 - a0) / BAY)); bw = (a1 - a0) / nb
                    cs = [a0 + (i + 0.5) * bw for i in range(nb)]
                    cs = [c for c in cs if r[3] + 1.4 <= c <= r[4] - 1.4]
                    if not cs: continue
                    step = 3 if (r[4] - r[3]) > 30 else 2
                    mid = (r[3] + r[4]) / 2
                    ci = min(range(len(cs)), key=lambda i: abs(cs[i] - mid))
                    if len(cs) % 2 == 0 and step == 2:      # even count: symmetric pairs around the centre (+-0.5, +-2.5 bays ...)
                        sel = [c for c in cs if round(abs(c - mid) / bw - 0.5) % 2 == 0]
                    else:
                        sel = [c for i, c in enumerate(cs) if (i - ci) % step == 0]
                    for c in sel:
                        w = min(2.6, bw - 0.9)
                        if not _doors_clear(r[0], r[1], band, c - w / 2, c + w / 2): continue
                        add(r[5], dict(u0=c - w / 2, u1=c + w / 2, z0=zb0 + 0.9, z1=ztop - 1.0, band=band, kind='hall', space=sp['id']))
                        n_hall += 1
                PLAN_LOG.append((sp['id'], band, 'hall', n_hall))
    return plan

def draw_window(acc, S, name, nrm, coord, w):
    G, W = 'Facade', 'Windows'
    u0, u1, z0, z1 = w['u0'], w['u1'], w['z0'], w['z1']
    gm = 'win_glass' if w['kind'] == 'room' else 'win_glass_g'
    S.box(acc, W, gm, u0, u1, 0.05, 0.08, z0, z1)
    ft = 0.16
    for (a0_, a1_, b0_, b1_) in ((u0 - ft, u0, z0 - (0.0 if w['kind'] == 'room' else ft), z1 + ft), (u1, u1 + ft, z0 - (0.0 if w['kind'] == 'room' else ft), z1 + ft),
                                  (u0, u1, z1, z1 + ft)) + (() if w['kind'] == 'room' else ((u0, u1, z0 - ft, z0),)):
        S.box(acc, G, 'frame_dark', a0_, a1_, 0.03, 0.10, b0_, b1_)
    nm = max(1, int(math.ceil((u1 - u0) / 1.5)) - 1)          # vertical mullions
    for k in range(1, nm + 1):
        uk = u0 + (u1 - u0) * k / (nm + 1)
        S.box(acc, G, 'frame_dark', uk - 0.05, uk + 0.05, 0.08, 0.14, z0, z1)
    nt = int((z1 - z0) / 2.6)                                    # transoms
    for k in range(1, nt + 1):
        zk = z0 + (z1 - z0) * k / (nt + 1)
        S.box(acc, G, 'frame_dark', u0, u1, 0.08, 0.14, zk - 0.05, zk + 0.05)
    S.box(acc, G, 'stone_trim', u0 - 0.35, u1 + 0.35, 0.0, 0.32, z1 + ft, z1 + ft + 0.32)   # lintel
    if w['kind'] == 'hall':
        S.box(acc, G, 'stone_trim', u0 - 0.2, u1 + 0.2, 0.0, 0.28, z0 - ft - 0.25, z0 - ft)  # sill
    reg(S, name, nrm, coord, u0, u1, z0, z1, w['band'])

def _exposed_runs(mass, name, nrm, coord, u0, u1, a0, a1, band, step=0.1):
    k = max(1, int(round((u1 - u0) / step))); us = [u0 + (u1 - u0) * i / k for i in range(k + 1)]
    okv = [visible(mass, name, nrm, coord, min(max((us[i] + us[i + 1]) / 2, a0 + 1e-3), a1 - 1e-3), band) for i in range(k)]
    runs, i = [], 0
    while i < k:
        if not okv[i]: i += 1; continue
        j = i
        while j < k and okv[j]: j += 1
        runs.append((us[i], us[j])); i = j
    return runs

def facades(acc, rng):
    G = 'Facade'; W = 'Windows'
    WINDOWS.clear(); PANES.clear(); SKIPPED.clear()
    PLAN.clear(); PLAN.update(plan_windows())
    stats = dict(bays=0)
    for mass in MASSES:
        h = mass['h']
        bands = ['L1', 'L2', 'L3'] + (['L4'] if h > 24 else [])
        if h <= 16: bands = ['L1', 'L2']
        for (name, nrm, coord, (a0, a1), axis) in side_defs(mass['rect']):
            L = a1 - a0
            nb = max(1, round(L / BAY))
            bw = L / nb
            S = Side(nrm, coord, axis)
            side_wins = PLAN.get((mass['name'], name), [])
            # door exclusion
            doors = [d for d in DOORS if not d['glass'] and d['axis'] == axis and False]
            for ib in range(nb):
                u0, u1 = a0 + ib * bw, a0 + (ib + 1) * bw
                uc = (u0 + u1) / 2
                vis = {b: visible(mass, name, nrm, coord, uc, b) for b in bands}
                wok = {b: False for b in bands}     # per-bay windows retired: windows now come from plan_windows() (one per room / hall rhythm)
                # entrance door exclusion (main door of lobby)
                door_here = any((d['axis'] == ('y' if axis == 'x' else 'x')) and abs(d['coord'] - coord) < 1e-3 and d['band'] == 'L1' and not d['glass']
                                and abs(d['center'] - uc) < bw / 2 + d['width'] / 2 and d['kind'] == 'main_door' for d in DOORS)
                # pilaster at u0 (and u1 on last bay)
                for pu in ([u0, u1] if ib == nb - 1 else [u0]):
                    if mass['name'] == 'CENTER_S' and name == 'S' and abs(pu) < 3.0 + 0.45: continue   # no pilaster inside the main doorway
                    pv = [b for b in bands if visible(mass, name, nrm, coord, min(max(pu, a0 + 0.3), a1 - 0.3), b)]
                    for b in pv:
                        if any(w['band'] == b and w['u0'] - 0.5 < pu < w['u1'] + 0.5 for w in side_wins): continue
                        zb0, zb1 = BAND_Z[b]; zt = min(zb1, h)
                        S.box(acc, G, 'stone_trim', pu - 0.38, pu + 0.38, 0.0, 0.42, max(zb0, 1.2) if b == 'L1' else zb0 + 0.3, zt - (1.4 if zt == h else 0.3))
                if not any(vis.values()): continue
                stats['bays'] += 1
                for b in bands:
                    if not vis[b]: continue
                    zb0, zb1 = BAND_Z[b]; zt = min(zb1, h)
                    top = (zt == h)
                    if b == 'L1':
                        if not door_here:
                            def plinth(pa, pb):
                                # only where this side is really exposed (a bay can be half covered by an adjoining wing: the
                                # plinth used to run on into that wing's room - found by the art-slot check)
                                k = max(1, int((pb - pa) / 0.1)); us = [pa + (pb - pa) * i / k for i in range(k + 1)]
                                okv = [visible(mass, name, nrm, coord, min(max((us[i] + us[i + 1]) / 2, a0 + 1e-3), a1 - 1e-3), 'L1') for i in range(k)]
                                i = 0
                                while i < k:
                                    if not okv[i]: i += 1; continue
                                    j = i
                                    while j < k and okv[j]: j += 1
                                    S.box(acc, G, 'stone_trim', us[i], us[j], 0.0, 0.18, 0.0, 1.2); i = j
                            cur = u0
                            for w in sorted([w for w in side_wins if w['band'] == 'L1' and w['u1'] > u0 and w['u0'] < u1], key=lambda w: w['u0']):
                                if w['u0'] - 0.15 > cur: plinth(cur, w['u0'] - 0.15)
                                cur = max(cur, w['u1'] + 0.15)
                            if u1 > cur: plinth(cur, u1)  # plinth (omitted in the doorway and under floor-to-ceiling glass)
                        if not door_here and wok['L1']:
                            w = 2.2
                            zs = 5.2
                            fr = arch_poly(uc, 1.4, w + 0.5, zs, 8)
                            wp = arch_poly(uc, 1.55, w, zs, 8)
                            for i in range(len(fr)):          # dark frame ring around the glass (no opaque plate behind it)
                                j = (i + 1) % len(fr)
                                acc.flat(G, 'frame_dark', [S.P(*fr[i][:1], 0.03, fr[i][1]), S.P(*fr[j][:1], 0.03, fr[j][1]), S.P(*wp[j][:1], 0.03, wp[j][1]), S.P(*wp[i][:1], 0.03, wp[i][1])], S.hint)
                            acc.flat(W, 'win_glass' if (ib + int(coord)) % 3 else 'win_glass_g', [S.P(u, 0.07, z) for u, z in wp], S.hint)
                            S.box(acc, G, 'frame_dark', uc - 0.05, uc + 0.05, 0.07, 0.13, 1.55, zs + w / 2)
                            S.box(acc, G, 'frame_dark', uc - w / 2, uc + w / 2, 0.07, 0.13, 3.4, 3.5)
                            reg(S, name, nrm, coord, uc - w / 2, uc + w / 2, 1.55, zs, 'L1')
                            reg(S, name, nrm, coord, uc - 0.55, uc + 0.55, zs, zs + 0.9, 'L1', with_pane=False)   # opening follows the arch head
                            # keystone
                            S.box(acc, G, 'stone_trim', uc - 0.25, uc + 0.25, 0.0, 0.3, zs + w / 2 + 0.3, zs + w / 2 + 0.9)
                    elif b == 'L2' and wok['L2']:
                        w = 1.8
                        gm = 'win_glass' if rng.random() > 0.15 else 'win_glass_g'
                        z0w, z1w = zb0 + 1.9, zb0 + 5.8
                        for (a0_, a1_, b0_, b1_) in ((uc - w / 2 - 0.2, uc - w / 2, z0w - 0.2, z1w + 0.2), (uc + w / 2, uc + w / 2 + 0.2, z0w - 0.2, z1w + 0.2),
                                                       (uc - w / 2, uc + w / 2, z0w - 0.2, z0w), (uc - w / 2, uc + w / 2, z1w, z1w + 0.2)):
                            S.box(acc, G, 'frame_dark', a0_, a1_, 0.03, 0.06, b0_, b1_)          # frame (4 bars) - the opening stays open
                        S.box(acc, W, gm, uc - w / 2, uc + w / 2, 0.05, 0.08, z0w, z1w)
                        reg(S, name, nrm, coord, uc - w / 2, uc + w / 2, z0w, z1w, 'L2')
                        S.box(acc, G, 'frame_dark', uc - 0.05, uc + 0.05, 0.08, 0.14, zb0 + 1.9, zb0 + 5.8)
                        S.box(acc, G, 'frame_dark', uc - w / 2, uc + w / 2, 0.08, 0.14, zb0 + 3.8, zb0 + 3.9)
                        S.box(acc, G, 'stone_trim', uc - w / 2 - 0.35, uc + w / 2 + 0.35, 0.0, 0.35, zb0 + 5.95, zb0 + 6.3)  # lintel
                        # pediment (triangle prism)
                        pa, pb = S.P(uc - w / 2 - 0.5, 0, 0), S.P(uc + w / 2 + 0.5, 0, 0)
                        tri = [(uc - w / 2 - 0.5, zb0 + 6.3), (uc + w / 2 + 0.5, zb0 + 6.3), (uc, zb0 + 7.2)]
                        if axis == 'x':
                            acc.prism(G, 'stone_trim', tri, 'xz', S.P(0, 0, 0)[1], S.P(0, 0.35, 0)[1] if nrm[1] > 0 else S.P(0, 0.35, 0)[1])
                        else:
                            acc.prism(G, 'stone_trim', tri, 'yz', S.P(0, 0, 0)[0], S.P(0, 0.35, 0)[0])
                        S.box(acc, G, 'stone_trim', uc - w / 2 - 0.2, uc + w / 2 + 0.2, 0.0, 0.3, zb0 + 1.6, zb0 + 1.9)  # sill
                    elif b == 'L3' and wok['L3']:
                        w = 1.4
                        z0w, z1w = zb0 + 1.95, zb0 + 4.85
                        for (a0_, a1_, b0_, b1_) in ((uc - w / 2 - 0.15, uc - w / 2, z0w - 0.15, z1w + 0.15), (uc + w / 2, uc + w / 2 + 0.15, z0w - 0.15, z1w + 0.15),
                                                       (uc - w / 2, uc + w / 2, z0w - 0.15, z0w), (uc - w / 2, uc + w / 2, z1w, z1w + 0.15)):
                            S.box(acc, G, 'frame_dark', a0_, a1_, 0.03, 0.06, b0_, b1_)
                        S.box(acc, W, 'win_glass', uc - w / 2, uc + w / 2, 0.05, 0.08, z0w, z1w)
                        reg(S, name, nrm, coord, uc - w / 2, uc + w / 2, z0w, z1w, 'L3')
                        S.box(acc, G, 'frame_dark', uc - 0.05, uc + 0.05, 0.08, 0.14, zb0 + 1.95, zb0 + 4.85)
                        S.box(acc, G, 'stone_trim', uc - w / 2 - 0.3, uc + w / 2 + 0.3, 0.0, 0.3, zb0 + 5.0, zb0 + 5.35)
                    elif b == 'L4' and wok['L4']:
                        w = 1.2
                        S.box(acc, W, 'win_glass_g', uc - w / 2, uc + w / 2, 0.05, 0.08, zb0 + 2.2, zb0 + 5.0)
                        for (a0_, a1_, b0_, b1_) in ((uc - w / 2 - 0.12, uc - w / 2, zb0 + 2.1, zb0 + 5.1), (uc + w / 2, uc + w / 2 + 0.12, zb0 + 2.1, zb0 + 5.1)):
                            S.box(acc, G, 'frame_dark', a0_, a1_, 0.03, 0.06, b0_, b1_)
                        reg(S, name, nrm, coord, uc - w / 2, uc + w / 2, zb0 + 2.2, zb0 + 5.0, 'L4')
                        S.box(acc, G, 'stone_trim', uc - w / 2 - 0.2, uc + w / 2 + 0.2, 0.0, 0.25, zb0 + 5.0, zb0 + 5.3)
                    # string course at band top - only along the exposed part of the bay (a bay half covered by an adjoining
                    # wing used to run its course on into that wing's room: a 0.35 m ledge on the floor once the wall there
                    # was removed, found by the t27u tower-open check)
                    for ra, rb in _exposed_runs(mass, name, nrm, coord, u0, u1, a0, a1, b):
                        if not top:
                            S.box(acc, G, 'stone_trim', ra, rb, 0.0, 0.42, zb1 - 0.35, zb1 + 0.35)
                        else:
                            S.box(acc, G, 'stone_trim', ra, rb, 0.0, 0.55, zt - 1.0, zt - 0.3)
                            S.box(acc, G, 'stone_trim', ra, rb, 0.0, 1.05, zt - 0.3, zt + 0.35)
                            S.box(acc, G, 'gold', ra, rb, 0.0, 1.1, zt + 0.35, zt + 0.5)
            for w in side_wins: draw_window(acc, S, name, nrm, coord, w)
    return stats

def central_portico(acc):
    G = 'Facade'
    for x in (-10.5, -4.5, 4.5, 10.5):
        acc.cyl(G, 'stone_trim', x, 8 - 0.4 - 1.7, 1.2, 22.4, 0.7, n=14)
        acc.box(G, 'stone_trim', x - 0.95, 8 - 0.4 - 2.65, 0.0, x + 0.95, 8 - 0.4 - 0.75, 1.2)
        acc.box(G, 'gold', x - 0.95, 8 - 0.4 - 2.65, 22.4, x + 0.95, 8 - 0.4 - 0.75, 22.8)
    acc.box(G, 'stone_trim', -12.5, 8 - 3.2, 22.8, 12.5, 8 - 0.2, 24.6)       # entablature
    acc.box(G, 'gold', -12.6, 8 - 3.3, 24.6, 12.6, 8 - 0.1, 24.9)
    # pediment tympanum (stone) in front of the slate gable
    tri = [(-13.2, 32.0), (13.2, 32.0), (0, 38.2)]
    if DORMER_OPEN:
        ring_prism(acc, G, 'stone_trim', tri, GABLE_WIN, 'xz', 8 - 0.9, 8 - 0.1)     # tympanum with a real window opening
    else:
        acc.prism(G, 'stone_trim', tri, 'xz', 8 - 0.9, 8 - 0.1)
    acc.flat('Windows', 'win_glass', [(p[0], 8 - 0.93, p[1]) for p in GABLE_WIN], (0, -1, 0))
    for i in range(3):   # thin dark frame on the glass edges
        p, q = GABLE_WIN[i], GABLE_WIN[(i + 1) % 3]
        acc.bar('Facade', 'frame_dark', (p[0], 8 - 0.97, p[1]), (q[0], 8 - 0.97, q[1]), 0.12, 0.08)
    pane((0.0, 8 - 0.93, (32.9 * 2 + 36.3) / 3), (0, -1), 0.07 + 0.8 + 0.5, 'gable')
    # entrance frame around the main door
    acc.box(G, 'frame_dark', -3.3, 8 - 0.45, 0, -3.0, 8 + 0.1, 5.4)
    acc.box(G, 'frame_dark', 3.0, 8 - 0.45, 0, 3.3, 8 + 0.1, 5.4)
    acc.box(G, 'gold', -3.3, 8 - 0.5, 5.2, 3.3, 8 + 0.1, 5.6)
    # (the old 0.5 m portico step is gone: the apron is flush with the plaza)
    lobby_auto_door(acc)

def lobby_auto_door(acc):
    """Bi-parting horizontal sliding glass door of the lobby entrance (6.0 x 5.0 m opening, two 3.0 m leaves)."""
    d = [d for d in DOORS if d['kind'] == 'main_door'][0]
    W, H, yc = d['width'], d['height'], d['coord'] - 0.9      # leaves ride on a rail in front of the facade
    for lname, x0, x1 in (('L', -W / 2, -0.01), ('R', 0.01, W / 2)):
        g = 'AutoDoor_LOBBY_' + lname
        acc.flat(g, 'glass', [(x0, yc, 0.0), (x1, yc, 0.0), (x1, yc, H - 0.05), (x0, yc, H - 0.05)], (0, -1, 0))
        t = 0.09
        acc.box(g, 'glass_frame', x0, yc - t / 2, 0.0, x1, yc + t / 2, 0.12)
        acc.box(g, 'glass_frame', x0, yc - t / 2, H - 0.17, x1, yc + t / 2, H - 0.05)
        acc.box(g, 'glass_frame', x0, yc - t / 2, 0.0, x0 + 0.1, yc + t / 2, H - 0.05)
        acc.box(g, 'glass_frame', x1 - 0.1, yc - t / 2, 0.0, x1, yc + t / 2, H - 0.05)
        DOOR_LEAVES.append(dict(name=g, side=lname, x0=x0, x1=x1, z0=0.0, z1=H, slide=W / 2, yc=yc, cx=0.0, w=W, h=H))
    # overhead track housing (covers the parked leaves)
    acc.box('Facade', 'frame_dark', -W - 0.2, yc - 0.12, H, W + 0.2, yc + 0.12, H + 0.22)

# ---------------------------------------------------------------- roof windows: real openings
DORMER_OPEN = True     # False = old behaviour (solid dormer block on an intact roof shell) - used by the selftest negative case
PANES = []             # every window glass pane: dict(c=centre, n=outward normal, clear=required open depth behind it, kind)

def pane(c, n, clear, kind, hz=0.4):
    PANES.append(dict(c=tuple(float(v) for v in c), n=(float(n[0]), float(n[1]), 0.0), clear=float(clear), kind=kind, hz=hz))

def holed_face(acc, G, mat, za, zb, s_of, alo, ahi, holes, mp, center):
    """planar roof face between heights za..zb: point = mp(s_of(z), a, z) for a in [alo(z), ahi(z)];
    rectangular holes (a0, a1, z0, z1) are left open (z-banded quads)."""
    zs = sorted(set([za, zb] + [h[k] for h in holes for k in (2, 3) if za < h[k] < zb]))
    faces = []
    for z0, z1 in zip(zs[:-1], zs[1:]):
        if z1 - z0 < 1e-6: continue
        cov = sorted([h for h in holes if h[2] <= z0 + 1e-6 and h[3] >= z1 - 1e-6], key=lambda h: h[0])
        edges = [('f', alo)] + [e for h in cov for e in (('c', h[0]), ('c', h[1]))] + [('f', ahi)]
        for k in range(0, len(edges), 2):
            (ka, va), (kb, vb) = edges[k], edges[k + 1]
            A = lambda z, kk, vv: vv(z) if kk == 'f' else vv
            a00, a01, a10, a11 = A(z0, ka, va), A(z0, kb, vb), A(z1, ka, va), A(z1, kb, vb)
            if max(a01 - a00, a11 - a10) < 1e-5: continue
            faces.append([mp(s_of(z0), a00, z0), mp(s_of(z0), a01, z0), mp(s_of(z1), a11, z1), mp(s_of(z1), a10, z1)])
    acc.add_faces_oriented(G, mat, faces, center)

def hollow_prism(acc, G, mat, prof, plane, a0, a1, holes_by_edge, center_z=None, bottom=True, caps=(True, True)):
    """closed roof prism built from faces so that dormer openings can be cut into its slanted edges."""
    mp = (lambda s, a, z: (s, a, z)) if plane == 'xz' else (lambda s, a, z: (a, s, z))
    c2 = np.mean(prof, 0); center = mp(c2[0], (a0 + a1) / 2, c2[1])
    n = len(prof)
    for i in range(n):
        (s0, z0), (s1, z1) = prof[i], prof[(i + 1) % n]
        if abs(z1 - z0) < 1e-6:
            if not bottom and i == n - 1: continue
            acc.add_faces_oriented(G, mat, [[mp(s0, a0, z0), mp(s1, a0, z1), mp(s1, a1, z1), mp(s0, a1, z0)]], center)
            continue
        lo = (s0, z0, s1, z1) if z0 < z1 else (s1, z1, s0, z0)
        sf = (lambda z, lo=lo: lo[0] + (lo[2] - lo[0]) * (z - lo[1]) / (lo[3] - lo[1]))
        holed_face(acc, G, mat, lo[1], lo[3], sf, lambda z: a0, lambda z: a1, holes_by_edge.get(i, []), mp, center)
    for a, on in zip((a0, a1), caps):
        if on: acc.add_faces_oriented(G, mat, [[mp(p[0], a, p[1]) for p in prof]], center)

def ring_faces(acc, G, mat, outer, inner, plane, a, hint):
    mp = (lambda p: (p[0], a, p[1])) if plane == 'xz' else (lambda p: (a, p[0], p[1]))
    for i in range(len(outer)):
        j = (i + 1) % len(outer)
        acc.flat(G, mat, [mp(outer[i]), mp(outer[j]), mp(inner[j]), mp(inner[i])], hint)

def ring_prism(acc, G, mat, outer, inner, plane, a0, a1):
    """prism with a polygonal hole (tympanum around a gable window)."""
    h = (0, 1, 0) if plane == 'xz' else (1, 0, 0)
    ring_faces(acc, G, mat, outer, inner, plane, a0, tuple(-v for v in h)); ring_faces(acc, G, mat, outer, inner, plane, a1, h)
    mp = (lambda p, a: (p[0], a, p[1])) if plane == 'xz' else (lambda p, a: (a, p[0], p[1]))
    co = np.mean(outer, 0)
    for poly, sgn in ((outer, 1), (inner, -1)):
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            mid = (np.array(poly[i]) + np.array(poly[j])) / 2 - co
            hint = mp((mid[0] * sgn, mid[1] * sgn), 0) if plane == 'xz' else mp((mid[0] * sgn, mid[1] * sgn), 0)
            hint = (hint[0], 0, hint[2]) if plane == 'xz' else (0, hint[1], hint[2])
            acc.flat(G, mat, [mp(poly[i], a0), mp(poly[j], a0), mp(poly[j], a1), mp(poly[i], a1)], hint)

def hollow_dormer(acc, R, fx, fy, n, zD, W, H, D, gw, gz0, gz1, kind, ft=0.15):
    """dormer as a real hollow box: front wall with the window opening, two cheeks, floor; open at the back where it
    meets the (holed) roof shell, so the glass looks into the attic / plant level. Glass pane sits 0.03 m proud."""
    t = (-n[1], n[0])
    def B(u0, u1, w0, w1, z0, z1, mat='stone_trim'):
        xa, ya = fx + t[0] * u0 - n[0] * w0, fy + t[1] * u0 - n[1] * w0
        xb, yb = fx + t[0] * u1 - n[0] * w1, fy + t[1] * u1 - n[1] * w1
        acc.box(R, mat, xa, ya, z0, xb, yb, z1)
    if DORMER_OPEN:
        B(-W, -gw, 0, ft, zD, zD + H); B(gw, W, 0, ft, zD, zD + H)
        B(-gw, gw, 0, ft, zD, gz0); B(-gw, gw, 0, ft, gz1, zD + H)
        B(-W, -W + ft, ft, D, zD, zD + H); B(W - ft, W, ft, D, zD, zD + H)
        B(-W, W, 0, D, zD - 0.15, zD)
    else:
        B(-W, W, 0, D, zD, zD + H)
    B(-gw, gw, -0.07, -0.03, gz0, gz1, 'win_glass_g') if False else None
    xa, ya = fx + t[0] * -gw + n[0] * 0.03, fy + t[1] * -gw + n[1] * 0.03
    xb, yb = fx + t[0] * gw + n[0] * 0.07, fy + t[1] * gw + n[1] * 0.07
    acc.box('Windows', 'win_glass_g', xa, ya, gz0, xb, yb, gz1)
    pane((fx + n[0] * 0.05, fy + n[1] * 0.05, (gz0 + gz1) / 2), n, 0.05 + D + 0.5, kind)
    # little gabled roof over the dormer
    if n[1] != 0:
        acc.prism(R, 'roof_metal', [(fx - W - 0.25, zD + H), (fx + W + 0.25, zD + H), (fx, zD + H + 1.0 * (W + 0.25) / 1.15)], 'xz', min(fy, fy - n[1] * D) - 0.1, max(fy, fy - n[1] * D) + 0.1)
    else:
        acc.prism(R, 'roof_metal', [(fy - W - 0.25, zD + H), (fy + W + 0.25, zD + H), (fy, zD + H + 1.0 * (W + 0.25) / 1.15)], 'yz', min(fx, fx - n[0] * D) - 0.1, max(fx, fx - n[0] * D) + 0.1)
    return (W - ft, zD, zD + H)   # half-width of the opening through the shell, z range

# t38u: roof / dome light strips use their own pale-yellow materials (neon_roof, neon_roof_ridge) in day AND night;
# neon_purple / neon_cyan elsewhere (screen frames, hologram, plaza, tower lantern) are unchanged
def roofs(acc, rng):
    R = 'Roofs'; N = 'Roofs'
    NW_FOOT = []    # north-wing roof footprints (they extend 10 m into the corner pavilions)
    for m in MASSES:
        if m['kind'] == 'nwing':
            x0, y0, x1, y1 = m['rect']; cxx = (x0 + x1) / 2
            NW_FOOT.append(((x0 - 10, x1) if cxx < 0 else (x0, x1 + 10)) + (40.0 - 10.2, 40.0 + 10.2))
    for m in MASSES:
        x0, y0, x1, y1 = m['rect']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if m['kind'] == 'pav':
            prof = [(24, 14.6), (31, 13.4), (38, 11.4), (44.2, 6.0)]
            rings = [acc.rect_ring(cx, cy, hh, hh, z) for z, hh in prof]
            # hollow mansard: open underneath so the L4 mech level / stair well inside it is real space
            # (a closed loft put a solid cap at z=24 that sealed the top of the corner-tower stairs)
            mansard_shell = True
            # cap & cresting
            acc.box(R, 'roof_cap', cx - 5.4, cy - 5.4, 44.0, cx + 6.1, cy + 6.1, 44.55)
            for z, hh in prof:
                for (ax, ay, bx, by) in [(-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)]:
                    acc.bar(N, 'neon_roof', (cx + ax * hh, cy + ay * hh, z + 0.1), (cx + bx * hh, cy + by * hh, z + 0.1), 0.28, 0.28)
            for sxx in (-1, 1):
                for syy in (-1, 1):
                    pts = [(cx + sxx * hh, cy + syy * hh, z + 0.1) for z, hh in prof]
                    for p0, p1 in zip(pts[:-1], pts[1:]):
                        acc.bar(N, 'neon_roof', p0, p1, 0.26, 0.26)
            # top lantern
            acc.cyl(R, 'roof_cap', cx, cy, 44.55, 45.6, 1.2, n=10, r1=0.8)
            acc.cyl(R, 'neon_cyan', cx, cy, 45.5, 46.0, 0.35, n=8)
            # dormers: hollow boxes; the mansard shell gets a matching opening behind each one
            zD, H, W = 27.0, 3.1, 0.9
            Z = [p[0] for p in prof]; HH = [p[1] for p in prof]
            dz = lambda z: float(np.interp(z, Z, HH))
            hx = dz(zD); D = (hx + 0.15) - dz(zD + H) + 0.25
            holes = {k: [] for k in range(4)}
            for side, nrm in enumerate([(0, -1), (1, 0), (0, 1), (-1, 0)]):
                t = (-nrm[1], nrm[0])
                for k in (-1, 0, 1):
                    u = k * 4.4
                    px, py = cx + nrm[0] * (hx + 0.15) + (u if nrm[1] != 0 else 0), cy + nrm[1] * (hx + 0.15) + (u if nrm[0] != 0 else 0)
                    if any(f[0] - 1.2 < px < f[1] + 1.2 and f[2] - 1.2 < py < f[3] + 1.2 for f in NW_FOOT):
                        SKIPPED.append((m['name'], 'dormer', round(u, 1), 'roof')); continue
                    hw, z0h, z1h = hollow_dormer(acc, R, px, py, nrm, zD, W, H, D, 0.6, zD + 0.5, zD + 2.6, 'dormer_tower')
                    ac = t[0] * (px - cx) + t[1] * (py - cy)
                    if DORMER_OPEN: holes[side].append((ac - hw, ac + hw, z0h, z1h))
            # mansard shell (open bottom = L4 plant level / stair well; closed top) with the dormer openings
            for side, nrm in enumerate([(0, -1), (1, 0), (0, 1), (-1, 0)]):
                t = (-nrm[1], nrm[0])
                mp = (lambda s_, a_, z_, nrm=nrm, t=t: (cx + nrm[0] * s_ + t[0] * a_, cy + nrm[1] * s_ + t[1] * a_, z_))
                for (za, ha), (zb, hb) in zip(prof[:-1], prof[1:]):
                    sf = (lambda z, za=za, zb=zb, ha=ha, hb=hb: ha + (hb - ha) * (z - za) / (zb - za))
                    hl = [h for h in holes[side] if h[2] >= za - 1e-6 and h[3] <= zb + 1e-6]
                    holed_face(acc, R, 'roof_metal', za, zb, sf, (lambda z, f=sf: -f(z)), sf, hl, mp, (cx, cy, 33))
            acc.add_faces_oriented(R, 'roof_metal', [list(rings[-1])], (cx, cy, 33))
        elif m['kind'] == 'wing':
            sgn = -1 if cx < 0 else 1
            prof = [(cx - 10.2, 24), (cx - 7.4, 28), (cx - 4, 31), (cx + 4, 31), (cx + 7.4, 28), (cx + 10.2, 24)]
            wing_holes = {0: [], 4: []}
            for xx in (cx - 4, cx + 4):
                acc.bar(N, 'neon_roof_ridge', (xx, -34, 31.1), (xx, 34, 31.1), 0.3, 0.3)
            for xx in (cx - 7.4, cx + 7.4):
                acc.bar(N, 'neon_roof', (xx, -34, 28.1), (xx, 34, 28.1), 0.2, 0.2)
            for xx, nsg in ((cx - 10.2, -1), (cx + 10.2, 1)):
                acc.bar(N, 'neon_roof', (xx, -34, 24.1), (xx, 34, 24.1), 0.22, 0.22)
            # dormers along both long sides (hollow, opening through the roof slope behind)
            sl = lambda z: 10.2 - 2.8 * (z - 24) / 4          # half-width of the lower roof slope at height z
            for yy in np.arange(-30, 31, 7.5):
                for nsg in (-1, 1):
                    zD, H, W = 25.4, 2.6, 0.8
                    xf = cx + nsg * (sl(zD) + 0.3)
                    D = (sl(zD) + 0.3) - sl(zD + H) + 0.25
                    hw, z0h, z1h = hollow_dormer(acc, R, xf, float(yy), (nsg, 0), zD, W, H, D, 0.5, zD + 0.4, zD + 2.2, 'dormer_wing')
                    if DORMER_OPEN: wing_holes[0 if nsg < 0 else 4].append((yy - hw, yy + hw, z0h, min(z1h, 28.0)))
            hollow_prism(acc, R, 'roof_metal', prof, 'xz', -44, 44, wing_holes)
        elif m['kind'] == 'nwing':
            xa, xb = (x0 - 10, x1) if cx < 0 else (x0, x1 + 10)
            cyy = 40.0
            prof = [(cyy - 10.2, 24), (cyy - 7.4, 28), (cyy - 4, 31), (cyy + 4, 31), (cyy + 7.4, 28), (cyy + 10.2, 24)]
            nw_holes = {0: [], 4: []}
            for yy in (cyy - 4, cyy + 4):
                acc.bar(N, 'neon_roof_ridge', (x0, yy, 31.1), (x1, yy, 31.1), 0.3, 0.3)
            for yy in (cyy - 7.4, cyy + 7.4):
                acc.bar(N, 'neon_roof', (x0, yy, 28.1), (x1, yy, 28.1), 0.2, 0.2)
            for yy in (cyy - 10.2, cyy + 10.2):
                acc.bar(N, 'neon_roof', (x0, yy, 24.1), (x1, yy, 24.1), 0.22, 0.22)
            sl = lambda z: 10.2 - 2.8 * (z - 24) / 4
            for xx in np.arange(x0 + 3, x1 - 2, 6.5):
                for nsg in (-1, 1):
                    zD, H, W = 25.4, 2.6, 0.8
                    yf = cyy + nsg * (sl(zD) + 0.3)
                    D = (sl(zD) + 0.3) - sl(zD + H) + 0.25
                    hw, z0h, z1h = hollow_dormer(acc, R, float(xx), yf, (0, nsg), zD, W, H, D, 0.5, zD + 0.4, zD + 2.2, 'dormer_nwing')
                    if DORMER_OPEN: nw_holes[0 if nsg < 0 else 4].append((xx - hw, xx + hw, z0h, min(z1h, 28.0)))
            hollow_prism(acc, R, 'roof_metal', prof, 'yz', xa, xb, nw_holes)
        elif m['kind'] == 'bump':
            sgn = -1 if cx < 0 else 1
            xo = x0 if sgn < 0 else x1       # outer edge
            xi = x1 if sgn < 0 else x0       # inner edge (against wing)
            prof = [(xo - sgn * 0.2, 16), (xo - sgn * -4 if False else xo + (-sgn) * -4, 22), (xi, 22), (xi, 16)]
            prof = [(xo + sgn * 0.2, 24), (xo - sgn * 3.2, 31), (xi, 31), (xi, 24)]
            acc.prism(R, 'roof_metal', prof, 'xz', y0 - 0.2, y1 + 0.2)
            acc.bar(N, 'neon_roof_ridge', (xo - sgn * 3.2, y0 - 0.2, 31.1), (xo - sgn * 3.2, y1 + 0.2, 31.1), 0.25, 0.25)
            acc.bar(N, 'neon_roof', (xo + sgn * 0.2, y0, 24.1), (xo + sgn * 0.2, y1, 24.1), 0.2, 0.2)
        elif m['kind'] == 'center':
            ctri = [(-14.4, 32), (14.4, 32), (0, 38)]
            if DORMER_OPEN:
                hollow_prism(acc, R, 'roof_metal', ctri, 'xz', 7.4, 32.0, {}, caps=(False, True))
                ring_faces(acc, R, 'roof_metal', ctri, GABLE_WIN, 'xz', 7.4, (0, -1, 0))
            else:
                acc.prism(R, 'roof_metal', ctri, 'xz', 7.4, 32.0)
            acc.bar(N, 'neon_cyan', (-14.4, 7.3, 32.15), (0, 7.3, 38.1), 0.2, 0.2) if False else None
            acc.bar(N, 'neon_roof', (0, 7.5, 38.1), (0, 32, 38.1), 0.25, 0.25)
            acc.bar(N, 'neon_roof', (-14.4, 7.4, 32.1), (0, 7.4, 38.0), 0.2, 0.2)
            acc.bar(N, 'neon_roof', (14.4, 7.4, 32.1), (0, 7.4, 38.0), 0.2, 0.2)
        elif m['kind'] == 'drum':
            # drum roof with a circular opening under the dome (atrium looks up into the dome)
            cy0, rr = DOME['c'][1], DOME['r'] - 0.3
            holes = []
            for k in range(28):
                ya, yb = cy0 - 14 + k, cy0 - 13 + k
                ym = min(abs(ya - cy0), abs(yb - cy0)); hw = math.sqrt(max(rr * rr - ym * ym, 0))
                if hw > 0.3: holes.append((-hw, ya, hw, yb))
            for r in rect_minus((-14.4, 31.6, 14.4, 60.4), holes):
                if r[2] - r[0] > 1e-3 and r[3] - r[1] > 1e-3:
                    acc.box(R, 'roof_metal', r[0], r[1], 31.7, r[2], r[3], 32.1)

def dome(acc):
    D = 'Dome'
    cx, cy = DOME['c']; r = DOME['r']; hh = DOME['h']; z0 = DOME['z0']
    n = 32; rings = []
    nz = 10
    thetas = [math.pi / 2 * k / nz for k in range(nz + 1)]
    for th in thetas[:-1]:
        rr = r * math.cos(th); z = z0 + hh * math.sin(th)
        rings.append([(cx + rr * math.cos(2 * math.pi * k / n), cy + rr * math.sin(2 * math.pi * k / n), z) for k in range(n)])
    # top ring tiny
    rr = r * 0.06; z = z0 + hh * 0.999
    rings.append([(cx + rr * math.cos(2 * math.pi * k / n), cy + rr * math.sin(2 * math.pi * k / n), z) for k in range(n)])
    acc.loft(D, 'glass_dome', rings, caps=False, center=(cx, cy, z0))
    # ribs
    nr = 16
    for k in range(nr):
        ph = 2 * math.pi * k / nr
        for a, b in zip(rings[:-1], rings[1:]):
            kk = int(round(k * n / nr)) % n
            p0, p1 = np.array(a[kk]), np.array(b[kk])
            # push slightly outward
            def out(p, e=0.12):
                v = np.array([p[0] - cx, p[1] - cy, p[2] - z0 + 0.0]); v /= (np.linalg.norm(v) + 1e-9)
                return p + v * e
            acc.bar(D, 'glass_frame', out(p0), out(p1), 0.42, 0.42, up=(math.cos(ph), math.sin(ph), 0))
    for ri in (2, 4, 6, 8):
        ring = rings[ri]
        for k in range(n):
            p0, p1 = np.array(ring[k]), np.array(ring[(k + 1) % n])
            def out(p, e=0.12):
                v = np.array([p[0] - cx, p[1] - cy, p[2] - z0]); v /= (np.linalg.norm(v) + 1e-9); return p + v * e
            acc.bar(D, 'glass_frame', out(p0), out(p1), 0.3, 0.3)
    # base ring with magenta neon + gold cornice ring
    base = rings[0]
    for k in range(n):
        p0, p1 = np.array(base[k]), np.array(base[(k + 1) % n])
        acc.bar('Dome', 'neon_roof', p0 + np.array([0, 0, 0.45]), p1 + np.array([0, 0, 0.45]), 0.3, 0.3)
        acc.bar(D, 'roof_cap', p0 + np.array([0, 0, 0.1]), p1 + np.array([0, 0, 0.1]), 0.9, 0.5)
    # arcs of neon along the dome (meridian, magenta) at four sides
    for k in (0, 8, 16, 24):
        for a, b in zip(rings[:-1], rings[1:]):
            acc.bar('Dome', 'neon_roof', np.array(a[k]) * 1.0 + np.array([0, 0, 0.0]), np.array(b[k]), 0.0, 0.0) if False else None
    # lantern + spire (z 44 -> 46)
    ztop = z0 + hh
    acc.cyl(D, 'roof_cap', cx, cy, ztop - 0.2, ztop + 0.9, 1.4, n=12, r1=1.0)
    acc.cyl(D, 'window_cyan', cx, cy, ztop + 0.9, ztop + 1.25, 0.6, n=10)
    acc.cyl('Dome', 'neon_roof', cx, cy, ztop + 1.25, 48.0, 0.07, n=6, r1=0.03)
    # drum corner turrets
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = 12.2 * sx, 46 + 13.0 * sy if False else 46 + 12.2 * sy
            acc.box(D, 'stone_trim', x - 1.6, y - 1.6, 32.0, x + 1.6, y + 1.6, 36.0)
            acc.box(D, 'window_purple', x - 0.4, y - 1.65 if False else y - 1.62, 33.0, x + 0.4, y - 1.58, 35.2) if False else None
            acc.loft(D, 'roof_metal', [acc.rect_ring(x, y, 1.9, 1.9, 36.0), acc.rect_ring(x, y, 0.2, 0.2, 38.8)], caps=True, center=(x, y, 37))
            acc.box(D, 'roof_cap', x - 1.8, y - 1.8, 35.7, x + 1.8, y + 1.8, 36.1)
            acc.bar('Dome', 'neon_roof', (x - 1.9, y - 1.9, 36.1), (x + 1.9, y - 1.9, 36.1), 0.15, 0.15)
            acc.bar('Dome', 'neon_roof', (x - 1.9, y + 1.9, 36.1), (x + 1.9, y + 1.9, 36.1), 0.15, 0.15)

DOOR_LEAVES = []   # registry of auto-door leaf groups: dict(name, side, x0, x1, z0, z1, slide)

def pyramid(acc, c, base, h, rows, cols, door_w, door_h, group='Pyramids', name='PYR'):
    cx, cy = c; b = base / 2
    # the doorway is exactly the two middle glass columns x the lowest rows -> bi-parting auto door, no sill/curb/frame in the way
    cw0 = base / cols; rh = h / rows
    assert abs(door_w - 2 * cw0) < 1e-6 and abs(door_h - round(door_h / rh) * rh) < 1e-6, (door_w, cw0, door_h, rh)
    door_rows = int(round(door_h / rh)); kmid = (cols // 2 - 1, cols // 2)
    sides = [((0, -1), (1, 0)), ((1, 0), (0, 1)), ((0, 1), (-1, 0)), ((-1, 0), (0, -1))]
    def P(side, u, z):
        n, t = side
        w = b * (1 - z / h)
        return (cx + n[0] * w + t[0] * u, cy + n[1] * w + t[1] * u, z)
    for si, side in enumerate(sides):
        for i in range(rows):
            z0, z1 = h * i / rows, h * (i + 1) / rows
            w0, w1 = b * (1 - z0 / h), b * (1 - z1 / h)
            for k in range(cols):
                s0, s1 = -1 + 2 * k / cols, -1 + 2 * (k + 1) / cols
                if si == 0 and i < door_rows and k in kmid: continue   # doorway (filled by the AutoDoor leaves)
                pts = [P(side, s0 * w0, z0), P(side, s1 * w0, z0), P(side, s1 * w1, z1), P(side, s0 * w1, z1)]
                if i == rows - 1:
                    pts = [pts[0], pts[1], P(side, 0, h)]
                acc.flat(group, 'glass', pts, (side[0][0], side[0][1], 0.4))
        # diamond lattice
        sp = base / (cols * 0.5)
        for fam in (1, -1):
            m = fam * 0.55 * (b / h) * 1.6
            c0 = -3 * b
            ks = np.arange(-int(4 * b / sp) - 2, int(4 * b / sp) + 3)
            for kk in ks:
                u0 = kk * sp
                # u(z) = u0 + m*z ; need |u| <= b(1 - z/h)
                lo, hi = 0.0, h
                # u <= b - b z/h  -> u0 + m z <= b - (b/h) z -> z (m + b/h) <= b - u0
                A = m + b / h
                if abs(A) > 1e-9:
                    z = (b - u0) / A
                    if A > 0: hi = min(hi, z)
                    else: lo = max(lo, z)
                # u >= -b + b z/h -> u0 + m z >= -b + (b/h) z -> z (m - b/h) >= -b - u0
                B = m - b / h
                if abs(B) > 1e-9:
                    z = (-b - u0) / B
                    if B > 0: lo = max(lo, z)
                    else: hi = min(hi, z)
                if hi - lo < 0.4: continue
                z_a, z_b = lo, hi
                if si == 0:   # keep the whole doorway (+0.35 m each side) free of lattice bars
                    clash = False
                    for tt in np.linspace(0, 1, 25):
                        zz = z_a + (z_b - z_a) * tt; uu = u0 + m * zz
                        if zz < door_h + 0.35 and abs(uu) < door_w / 2 * (1 - zz / h) + 0.35: clash = True; break
                    if clash: continue
                pa, pb = P(side, u0 + m * z_a, z_a), P(side, u0 + m * z_b, z_b)
                off = (side[0][0] * 0.06, side[0][1] * 0.06, 0)
                acc.bar(group, 'glass_frame', np.array(pa) + off, np.array(pb) + off, 0.07, 0.07)
    # frame: base edges + hips
    apex = (cx, cy, h)
    corners = [(cx - b, cy - b, 0), (cx + b, cy - b, 0), (cx + b, cy + b, 0), (cx - b, cy + b, 0)]
    for i in range(4):
        a, bb = corners[i], corners[(i + 1) % 4]
        if i == 0:   # south base edge with door gap
            acc.bar(group, 'glass_frame', a, (cx - door_w / 2 - 0.15, cy - b, 0), 0.3, 0.3)
            acc.bar(group, 'glass_frame', (cx + door_w / 2 + 0.15, cy - b, 0), bb, 0.3, 0.3)
        else:
            acc.bar(group, 'glass_frame', a, bb, 0.3, 0.3)
        acc.bar(group, 'glass_frame', a, apex, 0.28, 0.28)
    # door lintel (above the doorway only, bottom edge >= door_h)
    yl = cy - b + door_h * b / h
    acc.bar(group, 'glass_frame', (cx - door_w / 2 * (1 - door_h / h) - 0.1, yl, door_h + 0.13), (cx + door_w / 2 * (1 - door_h / h) + 0.1, yl, door_h + 0.13), 0.22, 0.22)
    # bi-parting sliding leaves, parallel to the sloping face (offset outwards so they slide in front of the fixed glass)
    nrm = np.array([0.0, -h, b]); nrm /= np.linalg.norm(nrm); off = nrm * 0.14
    side0 = sides[0]
    sc_t = 1 - door_h / h
    for lname, ua, ub in (('L', -door_w / 2, 0.0), ('R', 0.0, door_w / 2)):
        g = 'AutoDoor_%s_%s' % (name, lname)
        pad = 0.02 if lname == 'L' else 0.0
        ua2, ub2 = (ua, ub - 0.01) if lname == 'L' else (ua + 0.01, ub)
        p = [np.array(P(side0, ua2, 0.0)) + off, np.array(P(side0, ub2, 0.0)) + off,
             np.array(P(side0, ub2 * sc_t, door_h)) + off, np.array(P(side0, ua2 * sc_t, door_h)) + off]
        acc.flat(g, 'glass', [tuple(q) for q in p], (0, -1, 0.4))
        for q0, q1 in ((p[0], p[1]), (p[1], p[2]), (p[2], p[3]), (p[3], p[0])):
            acc.bar(g, 'glass_frame', q0, q1, 0.07, 0.07)
        xs = [q[0] for q in p]
        DOOR_LEAVES.append(dict(name=g, side=lname, x0=min(xs), x1=max(xs), z0=0.0, z1=door_h, slide=door_w / 2, yc=float(np.mean([q[1] for q in p])), cx=cx, w=door_w, h=door_h))
    # neon at the apex + base glow (base glow is cut at the doorway)
    for i in range(4):
        a, bb = corners[i], corners[(i + 1) % 4]
        if i == 0:
            acc.bar('Neon', 'neon_cyan', a, (cx - door_w / 2 - 0.15, cy - b, 0.12), 0.2, 0.12)
            acc.bar('Neon', 'neon_cyan', (cx + door_w / 2 + 0.15, cy - b, 0.12), bb, 0.2, 0.12)
        else:
            acc.bar('Neon', 'neon_cyan', (a[0], a[1], 0.12), (bb[0], bb[1], 0.12), 0.2, 0.12)
    acc.cyl('Neon', 'neon_cyan', cx, cy, h - 0.2, h + 0.4, 0.15, n=6)

def pyramids(acc, clear=True):
    if clear: DOOR_LEAVES.clear()
    pyramid(acc, PYR_MAIN['c'], PYR_MAIN['base'], PYR_MAIN['h'], 14, 18, 4.0, 4.5, name='PYR_MAIN')
    for ps in PYR_SMALL:
        pyramid(acc, ps['c'], ps['base'], ps['h'], 5, 10, 2.4, 2.8, name='PYR_S' + ('L' if ps['c'][0] < 0 else 'R'))
    # pools around the pyramids (ring of shallow water)
    for ps, m in [(PYR_MAIN, 2.2)] + [(p, 1.2) for p in PYR_SMALL]:
        cx, cy = ps['c']; b = ps['base'] / 2
        o0, o1 = b + 0.3, b + m
        gapw = 3.0 if ps is PYR_MAIN else 2.0
        rects = [(cx - o1, cy - o1, cx - o0, cy + o1), (cx + o0, cy - o1, cx + o1, cy + o1),
                 (cx - o0, cy + o0, cx + o0, cy + o1)]
        south = (cx - o0, cy - o1, cx + o0, cy - o0)
        rects += rect_minus(south, [(cx - gapw - 1, cy - o1 - 1, cx + gapw + 1, cy - o0 + 1)])
        for r in rects:
            if r[2] - r[0] > 0.05 and r[3] - r[1] > 0.05:
                acc.rect('Ground', 'water', r, 0.0, 0.12)
        # cyan rim lights
        acc.rect('Neon', 'neon_cyan', (cx - o1 - 0.15, cy - o1 - 0.15, cx - o1, cy + o1 + 0.15), 0.0, 0.2) if False else None

def screens(acc):
    G = 'Screens'
    spots = []
    # corner pavilion south faces (SW,SE) + inner courtyard faces of all four
    for sx in (-1, 1):
        spots.append(dict(side=('S', (0, -1), -60, 'x'), u=sx * 72.5, w=6.0, z0=6.0, z1=19.0, tex='screen_a' if sx < 0 else 'screen_b'))
        for sy in (-1, 1):
            xc = 54 * sx  # inner face coordinate
            spots.append(dict(side=('E' if sx < 0 else 'W', (1 if sx < 0 else -1, 0), -54 if sx < 0 else 54, 'y'),
                              u=sy * 47.0, w=6.0, z0=6.0, z1=19.0, tex='screen_b' if sy > 0 else 'screen_a'))
    for sp in spots:
        name, nrm, coord, axis = sp['side']
        S = Side(nrm, coord, axis)
        u0, u1 = sp['u'] - sp['w'] / 2, sp['u'] + sp['w'] / 2
        S.box(acc, G, 'frame_dark', u0 - 0.35, u1 + 0.35, 0.0, 0.55, sp['z0'] - 0.35, sp['z1'] + 0.35)
        a, b = S.P(u0, 0.58, sp['z0']), S.P(u1, 0.58, sp['z1'])
        pts = [S.P(u0, 0.58, sp['z0']), S.P(u1, 0.58, sp['z0']), S.P(u1, 0.58, sp['z1']), S.P(u0, 0.58, sp['z1'])]
        acc.flat(G, sp['tex'], pts, S.hint)
        S.box(acc, G, 'neon_purple', u0 - 0.35, u1 + 0.35, 0.0, 0.62, sp['z1'] + 0.35, sp['z1'] + 0.6)
        S.box(acc, G, 'neon_purple', u0 - 0.35, u1 + 0.35, 0.0, 0.62, sp['z0'] - 0.6, sp['z0'] - 0.35)

def ground(acc, rng):
    G = 'Ground'
    # earth block: solid below the B1 slab, but hollow where the B1 concourse / stair foyer actually are
    acc.box(G, 'ground', -170, -130, -8.0, 170, 130, -6.4)
    holes = [tuple(sp['rect']) for sp in spec.SPACES.values() if sp['level'] == 'B1']
    for r in rect_minus((-170, -130, 170, 130), holes):
        if r[2] - r[0] > 1e-3 and r[3] - r[1] > 1e-3:
            acc.box(G, 'ground', r[0], r[1], -6.4, r[2], r[3], -0.42)
    # street kerb ring + plinth glow
    acc.box(G, 'stone_dark', -96, -66, -0.42, 96, 66, -0.38) if False else None
    # lamp bollards in the courtyard
    for x in (-45, -30, 30, 45):
        for y in (-62, -20, 14):
            acc.cyl(G, 'frame_dark', x, y, 0, 1.0, 0.18, n=6)
            acc.box('Neon', 'window_warm', x - 0.12, y - 0.12, 1.0, x + 0.12, y + 0.12, 1.4)
    # cyan / purple ground strips in courtyard
    for x in (-40, -25, 25, 40):
        acc.box('Neon', 'neon_cyan', x - 0.1, -62, 0.0, x + 0.1, 10, 0.04) if False else None
    for y in (-62, -22, 20):
        acc.box('Neon', 'neon_purple', -53, y - 0.1, 0.0, 53, y + 0.1, 0.04) if False else None
    # light strips framing the courtyard pavement
    for (r) in [(-53.7, -69.7, -53.5, 29.7), (53.5, -69.7, 53.7, 29.7)]:
        acc.rect('Neon', 'neon_cyan', r, 0.0, 0.05)
    acc.rect('Neon', 'neon_cyan', (-53.7, -69.9, 53.7, -69.7), 0.0, 0.05)
    # roof deck for the lobby block north (flat roofs of low masses already covered by roofs)

def build_exterior(acc, seed=3):
    DOOR_LEAVES.clear()
    rng = random.Random(seed)
    st = facades(acc, rng)
    central_portico(acc)
    roofs(acc, rng)
    dome(acc)
    pyramids(acc, clear=False)
    screens(acc)
    ground(acc, rng)
    return st

if __name__ == '__main__':
    a = Acc(); spec.build(); print(build_exterior(a)); print(a.tri_by_group(), a.stats())
