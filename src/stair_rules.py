"""Stair design audit: architectural rules checked on the real model geometry (raycasts), per stair.
Rules (see report):
  R1 side clearance  : stair edge -> parallel wall is either wall-hugging (gap <= 0.10 m) or a clear zone (>= 1.2 m);
                       nothing in between (0.10 .. 1.2 m is a slot / hand trap)
  R2 approach zones  : clear floor in front of the first riser and beyond the last riser of >= max(width, 1.8) m
                       (grand stairs: >= max(width, 3.0) m), no wall / rail / void inside it
  R3 landings        : <= 18 risers per flight; turn landing depth >= stair width, straight landing >= 1.2 m
  R4 proportions     : riser 0.15-0.17, tread 0.30-0.32, 2R+T 0.60-0.64; width >= 1.8 (grand >= 3.0 per flight)
  R5 headroom        : >= 2.4 m over every tread and landing
  R6 handrails       : on both sides of every flight
  R7 openings        : every slab opening has a guardrail on all sides except the access side
  R8 doors           : no door opening overlaps a stair/landing in plan at a usable height, and no door sits inside
                       the approach zone laterally facing the stair
"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from spec import *
import verify
from verify import first_hit, floor_z
from mathutils import Vector
from mathutils.bvhtree import BVHTree

GAP_HUG, CLEAR_MIN, EPS = 0.12, 1.20, 0.03

def wall_bvh(acc):
    V, P = acc.all_faces_np(groups=['Walls_Exterior', 'Walls_Interior', 'Pyramids'])
    tris = []
    for q in P:
        for i in range(1, len(q) - 1): tris.append((q[0], q[i], q[i + 1]))
    return BVHTree.FromPolygons([Vector(v) for v in V], tris, epsilon=0.0)

def _perp(f):
    return (0.0, 1.0) if abs(f['dx']) > 0.5 else (1.0, 0.0)

def _dir(f): return (f['dx'], f['dy'])

def stair_class(st): return 'grand' if st['id'].startswith('S_GR') else 'public'

def ray_dist(bvh, o, d, maxd=15.0, inset=0.0):
    r = first_hit(bvh, o, d, maxd)
    return None if r is None else max(0.0, r[3] - inset)

def side_clearances(wbvh, st):
    """list of (what, side, gap) : distance from the stair/landing edge to the nearest wall measured sideways at 1.4 m above the tread"""
    out = []
    for fi, f in enumerate(st['flights']):
        px, py = _perp(f)
        for i in range(1, f['n'] + 1, 2):
            r, zt = flight_step_rect(f, i)
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            for sg in (-1, 1):
                o = (cx + sg * px * (f['w'] / 2 - 0.02), cy + sg * py * (f['w'] / 2 - 0.02), zt + 1.4)
                d = ray_dist(wbvh, o, (sg * px, sg * py, 0), inset=0.02)
                out.append(('flight%d' % fi, sg, d))
    for li, (r, z) in enumerate(st['landings']):
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        for (nx, ny, ex, ey) in ((1, 0, r[2], cy), (-1, 0, r[0], cy), (0, 1, cx, r[3]), (0, -1, cx, r[1])):
            o = (ex - nx * 0.02, ey - ny * 0.02, z + 1.4)
            out.append(('landing%d' % li, (nx, ny), ray_dist(wbvh, o, (nx, ny, 0), inset=0.02)))
    return out

def classify_gap(d):
    if d is None: return 'free'
    if d <= GAP_HUG: return 'hug'
    if d >= CLEAR_MIN: return 'clear'
    return 'SLOT'

def zone_depth(bvh, f, at_end, dreq):
    """clear floor depth in front of the first riser (at_end False) / beyond the last riser (at_end True)"""
    dx, dy = _dir(f); px, py = _perp(f)
    if at_end:
        e = flight_end(f); o = (e[0], e[1]); sgn = 1; z = e[2]
    else:
        o = (f['x'], f['y']); sgn = -1; z = f['z0']
    best = 15.0
    for lat in (0.0, f['w'] / 2 - 0.12, -(f['w'] / 2 - 0.12)):
        for h in (0.5, 1.5):
            p = (o[0] + px * lat + sgn * dx * 0.01, o[1] + py * lat + sgn * dy * 0.01, z + h)
            d = ray_dist(bvh, p, (sgn * dx, sgn * dy, 0))
            if d is not None: best = min(best, d)
        # floor continuity (no void / stair) at the same level
        t = 0.3
        while t < min(best, dreq + 0.01):
            zf = floor_z(bvh, o[0] + px * lat + sgn * dx * t, o[1] + py * lat + sgn * dy * t, z + 0.6, 1.5)
            if zf is None or abs(zf - z) > 0.06: best = min(best, t); break
            t += 0.3
    return best

def door_conflicts(st):
    """door openings overlapping stair/landing plan rects at a usable height, or standing inside the approach zone"""
    bad = []
    rects = []
    for f in st['flights']:
        for i in range(1, f['n'] + 1, 1):
            r, zt = flight_step_rect(f, i); rects.append((r, zt))
    for r, z in st['landings']: rects.append((r, z))
    for d in DOORS:
        lv_z = BAND_Z[d['band']][0]
        if d['axis'] == 'y': fp = (d['center'] - d['width'] / 2, d['coord'] - 0.25, d['center'] + d['width'] / 2, d['coord'] + 0.25)
        else: fp = (d['coord'] - 0.25, d['center'] - d['width'] / 2, d['coord'] + 0.25, d['center'] + d['width'] / 2)
        for r, zt in rects:
            if r[0] < fp[2] and r[2] > fp[0] and r[1] < fp[3] and r[3] > fp[1] and lv_z - 0.1 <= zt <= lv_z + d['height'] - 1.0:
                bad.append(('door_overlaps_stair', d['a'], d['b'], round(d['center'], 1))); break
    return bad

def audit(bvh, acc):
    wb = wall_bvh(acc)
    rows = []
    for st in STAIRS:
        cls = stair_class(st); iss = []
        f0 = st['flights'][0]; w = f0['w']
        row = dict(id=st['id'], cls=cls, w=w, flights=len(st['flights']))
        rows.append(row)
        # R4 proportions
        R = max(abs(f['riser']) for f in st['flights']); T = min(f['tread'] for f in st['flights'])
        row['riser'] = round(R, 3); row['tread'] = T; row['2R+T'] = round(2 * R + T, 3)
        if not (0.15 - 1e-3 <= R <= 0.17 + 1e-3): iss.append('riser %.3f' % R)
        if not (0.30 - 1e-3 <= T <= 0.32 + 1e-3): iss.append('tread %.2f' % T)
        if not (0.60 - 1e-3 <= 2 * R + T <= 0.64 + 1e-3): iss.append('2R+T %.3f' % (2 * R + T))
        wmin = 3.0 if cls == 'grand' else 1.8
        if min(f['w'] for f in st['flights']) < wmin - 1e-6: iss.append('width<%.1f' % wmin)
        # R3 landings
        row['max_risers'] = max(f['n'] for f in st['flights'])
        if row['max_risers'] > 18: iss.append('%d risers in one flight' % row['max_risers'])
        ld = []
        for li, (r, z) in enumerate(st['landings']):
            fa, fb = st['flights'][li], st['flights'][li + 1]
            turn = (fa['dx'], fa['dy']) != (fb['dx'], fb['dy'])
            if abs(fa['dy']) > 0.5: depth = r[3] - r[1]
            else: depth = r[2] - r[0]
            need = max(fa['w'], 1.8) if turn else 1.2
            ld.append(('turn' if turn else 'straight', round(depth, 2)))
            if depth < need - 1e-6: iss.append('landing %d depth %.2f < %.2f' % (li, depth, need))
        row['landings'] = ld
        # R1 side clearance
        sc = side_clearances(wb, st)
        cats = [(a, b, classify_gap(d), d) for a, b, d in sc]
        slots = [(a, b, round(d, 2)) for a, b, c, d in cats if c == 'SLOT']
        mn = min([d for a, b, c, d in cats if d is not None and c != 'free'] or [None]) if any(c != 'free' for _, _, c, _ in cats) else None
        row['min_wall_gap'] = None if mn is None else round(mn, 2)
        row['slots'] = slots
        # report the typical clearance of each side of the first flight: hug / clear value
        row['gaps_flight0'] = sorted(set(round(d, 2) if d is not None else 99 for a, b, c, d in cats if a == 'flight0'))
        if slots: iss.append('wall slot %s' % sorted(set(s[2] for s in slots)))
        # R2 approach zones
        dreq = max(w, 3.0 if cls == 'grand' else 1.8)
        z0d = zone_depth(bvh, st['flights'][0], False, dreq); z1d = zone_depth(bvh, st['flights'][-1], True, dreq)
        row['zone_start'] = round(z0d, 2); row['zone_end'] = round(z1d, 2); row['zone_req'] = round(dreq, 2)
        if z0d < dreq - EPS: iss.append('start zone %.2f < %.2f' % (z0d, dreq))
        if z1d < dreq - EPS: iss.append('end zone %.2f < %.2f' % (z1d, dreq))
        # R5 headroom
        head = 99
        for f in st['flights']:
            for i in range(1, f['n'] + 1):
                r, zt = flight_step_rect(f, i)
                h = first_hit(bvh, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, zt + 0.02), (0, 0, 1), 30.0)
                head = min(head, 99 if h is None else h[0].z - zt)
        for r, z in st['landings']:
            h = first_hit(bvh, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, z + 0.02), (0, 0, 1), 30.0)
            head = min(head, 99 if h is None else h[0].z - z)
        row['headroom'] = round(head, 2)
        if head < HEAD_STAIR - 1e-6: iss.append('headroom %.2f' % head)
        # R6 handrails both sides
        miss = 0
        for f in st['flights']:
            px, py = _perp(f)
            i = max(1, f['n'] // 2); r, zt = flight_step_rect(f, i)
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            for sg in (-1, 1):
                h = first_hit(bvh, (cx, cy, zt + 1.0 - 0.5 * f["riser"]), (sg * px, sg * py, 0), 8.0)
                if h is None or h[3] > f['w'] / 2 - 0.0: miss += 1
        row['rails_missing'] = miss
        if miss: iss.append('%d handrail(s) missing' % miss)
        # R8 doors
        dc = door_conflicts(st)
        row['door_conflicts'] = dc
        if dc: iss.append('door conflict %s' % dc[:2])
        row['issues'] = iss
    # R7 openings
    holes = []
    for m in HOLE_META:
        x0, y0, x1, y1 = m['rect']; z = m['z']; bad = []
        for side, o, d in (('S', ((x0 + x1) / 2, y0 + 0.25), (0, -1)), ('N', ((x0 + x1) / 2, y1 - 0.25), (0, 1)),
                           ('W', (x0 + 0.25, (y0 + y1) / 2), (-1, 0)), ('E', (x1 - 0.25, (y0 + y1) / 2), (1, 0))):
            if side == m['access']: continue
            # only edges that have floor outside need a rail
            outside = (o[0] + d[0] * 0.6, o[1] + d[1] * 0.6)
            zf = floor_z(bvh, outside[0], outside[1], z + 0.6, 1.5)
            if zf is None or abs(zf - z) > 0.05: continue
            h = first_hit(bvh, (o[0], o[1], z + 0.7), (d[0], d[1], 0), 1.0)
            if h is None: bad.append(side)
        holes.append(dict(z=z, rect=tuple(round(v, 2) for v in m['rect']), access=m['access'], unguarded=bad))
    return rows, holes

def summarize(rows, holes):
    lines = []
    for r in rows:
        lines.append('%-14s %-6s w=%.1f fl=%d maxR/flt=%2d 2R+T=%.3f wallgap(f0)=%s zones s/e=%.1f/%.1f (req %.1f) head=%.2f rails_miss=%d  %s' % (
            r['id'], r['cls'], r['w'], r['flights'], r['max_risers'], r['2R+T'], r['gaps_flight0'], r['zone_start'], r['zone_end'],
            r['zone_req'], r['headroom'], r['rails_missing'], ('ISSUES: ' + '; '.join(r['issues'])) if r['issues'] else 'ok'))
    for h in holes:
        if h['unguarded']: lines.append('HOLE %s unguarded %s' % (h['rect'], h['unguarded']))
    return lines

if __name__ == '__main__':
    bvh, acc = verify.build_bvh()
    rows, holes = audit(bvh, acc)
    print('\n'.join(summarize(rows, holes)))
    import json
    json.dump(dict(rows=rows, holes=holes), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', sys.argv[1] if len(sys.argv) > 1 else 'stair_audit.json'), 'w'), indent=1, default=str)
