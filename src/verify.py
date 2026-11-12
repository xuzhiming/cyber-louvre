"""Circulation verification: walk graph + geometric (raycast) checks on the real model geometry."""
import os, sys, json, math, collections
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from spec import *
from geom import Acc
import arch, exterior, props, art
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BLOCK_GROUPS = ['Walls_Exterior', 'Walls_Interior', 'Slabs', 'Stairs', 'Rails', 'Pyramids', 'Ground', 'Roofs', 'Dome', 'Facade', 'Windows']
# NOTE: Roofs/Dome/Facade were missing before (round 'top stairs'): the mansard roof solid sealing the corner-tower stair tops was invisible to every check

def build_bvh():
    spec.build()
    acc = Acc(); arch.build_arch(acc); exterior.build_exterior(acc)
    V, P = acc.all_faces_np(groups=BLOCK_GROUPS)
    tris = []
    for q in P:
        for i in range(1, len(q) - 1): tris.append((q[0], q[i], q[i + 1]))
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], tris, epsilon=0.0)
    return bvh, acc

def first_hit(bvh, o, d, maxd):
    d = Vector(d); L = d.length
    if L < 1e-9: return None
    r = bvh.ray_cast(Vector(o), d.normalized(), maxd)
    return r if r[0] is not None else None

def floor_z(bvh, x, y, zfrom, maxd=6.0):
    r = first_hit(bvh, (x, y, zfrom), (0, 0, -1), maxd)
    return None if r is None else r[0].z

def seg_clear(bvh, P, Q, heights=(0.5, 1.2, 1.8)):
    P = np.array(P, float); Q = np.array(Q, float)
    d = Q - P; L = np.linalg.norm(d)
    if L < 1e-6: return True, None
    for h in heights:
        o = P + np.array([0, 0, h]); t = Q + np.array([0, 0, h])
        r = first_hit(bvh, o, t - o, np.linalg.norm(t - o))
        if r is not None: return False, (tuple(np.round(r[0], 2)), h)
    return True, None

def floor_ok(bvh, P, Q, step=0.5, tol=0.32):
    P = np.array(P, float); Q = np.array(Q, float)
    L = np.linalg.norm(Q - P); n = max(1, int(L / step))
    for i in range(n + 1):
        p = P + (Q - P) * i / n
        z = floor_z(bvh, p[0], p[1], p[2] + 0.45 + tol)
        if z is None or abs(z - p[2]) > tol: return False, (tuple(np.round(p, 2)), z)
    return True, None

def walk_segment(bvh, P, Q):
    """straight walk P->Q (x,y,z of floor); fall back to 1-waypoint detours"""
    ok1, e1 = seg_clear(bvh, P, Q); ok2, e2 = floor_ok(bvh, P, Q)
    if ok1 and ok2: return [P, Q], None
    P = np.array(P, float); Q = np.array(Q, float)
    d = Q - P; d[2] = 0; L = np.linalg.norm(d)
    if L > 1e-6:
        nrm = np.array([-d[1], d[0], 0]) / L
        for off in (3, -3, 6, -6, 9, -9, 12, -12):
            W = (P + Q) / 2 + nrm * off; W[2] = (P[2] + Q[2]) / 2
            a = seg_clear(bvh, P, W); b = floor_ok(bvh, P, W); c = seg_clear(bvh, W, Q); e = floor_ok(bvh, W, Q)
            if a[0] and b[0] and c[0] and e[0]: return [P, W, Q], None
    return None, (e1, e2)

def door_world(d):
    zb0 = BAND_Z[d['band']][0]
    if d['axis'] == 'x':   # wall at x=coord, runs along y ; walk direction = x
        return (d['coord'], d['center'], zb0), (1, 0)
    return (d['center'], d['coord'], zb0), (0, 1)

def check_doors(bvh):
    res = []
    for d in DOORS:
        (cx, cy, z0), n = door_world(d)
        n = np.array(n + (0,), float); t = np.array([-n[1], n[0], 0.0])
        c = np.array([cx, cy, z0])
        hs = [0.3, 1.0, 1.9, min(d['height'] - 0.25, 2.8)]
        blocked = []
        for h in hs:
            o = c - n * 1.6 + np.array([0, 0, h])
            r = first_hit(bvh, o, n, 3.2)
            if r is not None: blocked.append((h, tuple(np.round(r[0], 2))))
        # wall present beside the opening
        side_hits = 0
        for s in (-1, 1):
            o = c - n * 1.6 + t * s * (d['width'] / 2 + 0.7) + np.array([0, 0, 1.0])
            if d['glass']:   # pyramids: faces slope, take a long ray
                r = first_hit(bvh, o, n, 12.0)
            else:
                r = first_hit(bvh, o, n, 3.2)
            if r is None and not d['glass']:
                # corner jamb: the opening sits right at a wall corner (t27u: tower hall <-> stair-shaft door now ends on the
                # opened hall/lobby line, the shaft's own south wall is its jamb) -> a wall within 0.5 m beside the opening
                r = first_hit(bvh, c + np.array([0, 0, 1.0]), t * s, d['width'] / 2 + 0.5)
            side_hits += 1 if r is not None else 0
        # lintel above the opening (not for glass; the pyramid frame bar is the lintel there)
        lint = None
        if not d['glass']:
            o = c - n * 1.6 + np.array([0, 0, d['height'] + 0.15])
            lint = first_hit(bvh, o, n, 3.2) is not None
        # floor each side
        fl = []
        for s in (-1, 1):
            p = c + n * s * 1.2
            z = floor_z(bvh, p[0], p[1], z0 + 1.0, 4.0)
            fl.append(z)
        floors_ok = all(z is not None and abs(z - z0) < 0.05 for z in fl) or d['kind'] == 'main_door' and False
        res.append(dict(a=d['a'], b=d['b'], kind=d['kind'], glass=d['glass'], width=d['width'], height=d['height'], cut=(len(blocked) == 0),
                        wall_beside=(side_hits == 2), lintel=lint, floor_both_sides=floors_ok, blocked=blocked, floors=fl))
    return res

def check_stairs(bvh):
    out = []
    for st in STAIRS:
        rec = dict(id=st['id'], a=st['a'], b=st['b'], flights=len(st['flights']), max_riser=0, min_tread=9, min_head=99, steps=0, fails=[])
        for fi, f in enumerate(st['flights']):
            rec['max_riser'] = max(rec['max_riser'], abs(f['riser'])); rec['min_tread'] = min(rec['min_tread'], f['tread'])
            for i in range(1, f['n'] + 1):
                r, zt = flight_step_rect(f, i)
                cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                z = floor_z(bvh, cx, cy, zt + 0.7, 2.0)
                if z is None or abs(z - zt) > 0.02:
                    rec['fails'].append(('tread_missing', f['x'], fi, i, z, zt)); continue
                hit = first_hit(bvh, (cx, cy, zt + 0.02), (0, 0, 1), 30.0)
                head = 99 if hit is None else hit[0].z - zt
                rec['min_head'] = min(rec['min_head'], head); rec['steps'] += 1
                if head < HEAD_MIN: rec['fails'].append(('headroom', fi, i, round(head, 2)))
        for lr, lz in st['landings']:
            cx, cy = (lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2
            z = floor_z(bvh, cx, cy, lz + 0.7, 2.0)
            hit = first_hit(bvh, (cx, cy, lz + 0.02), (0, 0, 1), 30.0)
            head = 99 if hit is None else hit[0].z - lz
            rec['min_head'] = min(rec['min_head'], head)
            if z is None or abs(z - lz) > 0.02: rec['fails'].append(('landing_missing', lz))
            if head < HEAD_MIN: rec['fails'].append(('landing_headroom', round(head, 2)))
        # arrival floors at both ends
        f0, fl = st['flights'][0], st['flights'][-1]
        ex = flight_end(fl)
        p0 = (f0['x'] - f0['dx'] * 0.35, f0['y'] - f0['dy'] * 0.35, f0['z0'])
        p1 = (ex[0] + fl['dx'] * 0.35, ex[1] + fl['dy'] * 0.35, ex[2])
        for nm, p in (('start', p0), ('end', p1)):
            z = floor_z(bvh, p[0], p[1], p[2] + 0.7, 2.0)
            if z is None or abs(z - p[2]) > 0.05: rec['fails'].append(('no_landing_floor_at_' + nm, tuple(np.round(p, 2)), z))
        # continuity between flights
        for a, b in zip(st['flights'][:-1], st['flights'][1:]):
            e = flight_end(a)
            if abs(e[2] - b['z0']) > 1e-6: rec['fails'].append(('z_gap_between_flights', e[2], b['z0']))
        rec['ok'] = not rec['fails']
        out.append(rec)
    return out


HEAD_WELL = 2.1
def check_windows(bvh, acc):
    """Every window opening cut through an exterior wall: (1) the glass pane (group 'Windows') must stop a walker from the
    outside (ray at 3 heights hits the pane first, within the facade depth), (2) without the pane the opening must be truly
    open (ray continues > wall thickness + 1 m into the room), i.e. the glass is real see-through glass and not a painted
    rectangle on a solid wall."""
    V, P = acc.all_faces_np(groups=['Walls_Exterior'])   # the opening must be cut through the exterior wall itself (frame bars / stairs behind it do not count)
    tris = [(q[0], q[i], q[i + 1]) for q in P for i in range(1, len(q) - 1)]
    bvh_nw = BVHTree.FromPolygons([Vector(v) for v in V], tris, epsilon=0.0)
    cuts = list(arch.WINDOW_CUTS); res = dict(cuts=len(cuts), glass_blocked=0, open_through=0, glass_fail=[], open_fail=[])
    for c in cuts:
        um, zm = (c['a0'] + c['a1']) / 2, (c['z0'] + c['z1']) / 2
        n = c['out']; ok_g = ok_o = True
        for zz in (c['z0'] + 0.25, zm, c['z1'] - 0.25):
            ox = (c['coord'] + n * 1.2, um) if c['axis'] == 'x' else (um, c['coord'] + n * 1.2)
            o = (ox[0], ox[1], zz); d = (-n, 0, 0) if c['axis'] == 'x' else (0, -n, 0)
            r = first_hit(bvh, o, d, 4.0)
            if r is None or r[1].dot(Vector(d)) == 0 or abs(r[0].x - o[0]) + abs(r[0].y - o[1]) > 0.75: ok_g = False
            r2 = first_hit(bvh_nw, o, d, 4.0)
            if r2 is not None and abs(r2[0].x - o[0]) + abs(r2[0].y - o[1]) < 0.8 + 1.2 + 0.5: ok_o = False
        res['glass_blocked'] += ok_g; res['open_through'] += ok_o
        if not ok_g and len(res['glass_fail']) < 6: res['glass_fail'].append((c['axis'], c['coord'], round(um, 1), round(zm, 1)))
        if not ok_o and len(res['open_fail']) < 6: res['open_fail'].append((c['axis'], c['coord'], round(um, 1), round(zm, 1)))
    return res

PANE_GROUPS = ['Walls_Exterior', 'Walls_Interior', 'Slabs', 'Roofs', 'Dome', 'Facade', 'Pyramids']

def check_panes(acc):
    """EVERY window glass pane (facade + roof dormers + gable): a ray from the pane centre straight inwards, with the
    glass itself ignored, must not hit wall / roof / facade within the pane's required open depth (wall or dormer
    depth + 0.5 m) - i.e. there is a real cut behind the glass into interior space, not a solid wall or roof shell."""
    V, P = acc.all_faces_np(groups=PANE_GROUPS)
    tris = [(q[0], q[i], q[i + 1]) for q in P for i in range(1, len(q) - 1)]
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], tris, epsilon=0.0)
    res = dict(panes=len(exterior.PANES), ok=0, by_kind={}, fails=[])
    for p in exterior.PANES:
        c = Vector(p['c']); d = Vector((-p['n'][0], -p['n'][1], 0.0)); hz = p.get('hz', 0.4)
        hits = [bvh.ray_cast(c + Vector((0, 0, dz)), d, p['clear']) for dz in (-hz, 0.0, hz)]
        ok = sum(h[0] is None for h in hits) >= 2      # a stair landing crossing a stairwell window may block one sample
        h = [x for x in hits if x[0] is not None][0] if not ok else None
        k = res['by_kind'].setdefault(p['kind'], [0, 0]); k[0] += 1; k[1] += ok
        res['ok'] += ok
        if not ok and len(res['fails']) < 8: res['fails'].append((p['kind'], tuple(round(x, 2) for x in p['c']), round(h[3], 2)))
    return res

def check_stair_wells(bvh):
    """For every stair: sample the clear height over EVERY step (centre + both sides), every landing and the arrival floor
    (0.3 .. 2.0 m beyond the top step) with all blocking geometry (incl. roofs / dome / facade) - must be >= HEAD_WELL;
    the arrival floor must be continuous at the top-step level (no slab above, no gap, no step)."""
    out = []
    for st in STAIRS:
        rec = dict(id=st['id'], top_z=None, min_head=99, worst=None, arrival_floor_fail=[], fails=[])
        def head_at(x, y, z):
            h = first_hit(bvh, (x, y, z + 0.02), (0, 0, 1), 60.0)
            return 99 if h is None else h[0].z - z
        for f in st['flights']:
            px, py = (0.0, 1.0) if abs(f['dx']) > 0.5 else (1.0, 0.0)
            for i in range(1, f['n'] + 1):
                r, zt = flight_step_rect(f, i); cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                for lat in (0.0, f['w'] / 2 - 0.2, -(f['w'] / 2 - 0.2)):
                    hh = head_at(cx + px * lat, cy + py * lat, zt)
                    if hh < rec['min_head']: rec['min_head'] = hh; rec['worst'] = (round(cx, 1), round(cy, 1), round(zt, 2))
        for r, z in st['landings']:
            for (x, y) in (((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), (r[0] + 0.3, r[1] + 0.3), (r[2] - 0.3, r[3] - 0.3)):
                hh = head_at(x, y, z)
                if hh < rec['min_head']: rec['min_head'] = hh; rec['worst'] = (round(x, 1), round(y, 1), round(z, 2))
        fl = st['flights'][-1]; e = flight_end(fl); rec['top_z'] = round(e[2], 3)
        px, py = (0.0, 1.0) if abs(fl['dx']) > 0.5 else (1.0, 0.0)
        for d in (0.3, 0.8, 1.4, 2.0):
            for lat in (0.0, fl['w'] / 2 - 0.2, -(fl['w'] / 2 - 0.2)):
                x, y = e[0] + fl['dx'] * d + px * lat, e[1] + fl['dy'] * d + py * lat
                hh = head_at(x, y, e[2])
                if hh < rec['min_head']: rec['min_head'] = hh; rec['worst'] = (round(x, 1), round(y, 1), round(e[2], 2))
                zf = floor_z(bvh, x, y, e[2] + 0.6, 1.5)
                if zf is None or abs(zf - e[2]) > 0.05: rec['arrival_floor_fail'].append((round(d, 1), round(lat, 1), zf))
        if rec['min_head'] < HEAD_WELL: rec['fails'].append(('headroom %.2f < %.1f at %s' % (rec['min_head'], HEAD_WELL, rec['worst'])))
        if rec['arrival_floor_fail']: rec['fails'].append(('arrival floor not continuous at top step z=%.2f' % e[2], rec['arrival_floor_fail'][:3]))
        rec['min_head'] = round(rec['min_head'], 2); rec['ok'] = not rec['fails']
        out.append(rec)
    return out

def stair_polyline(st):
    pts = []
    for fi, f in enumerate(st['flights']):
        for i in range(1, f['n'] + 1):
            r, zt = flight_step_rect(f, i)
            pts.append(((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, zt))
        if fi < len(st['flights']) - 1 and st['landings']:
            lr, lz = st['landings'][min(fi, len(st['landings']) - 1)]
            pts.append(((lr[0] + lr[2]) / 2, (lr[1] + lr[3]) / 2, lz))
    return pts

def anchor3(sp):
    x, y = sp['anchor']; return np.array([x, y, sp['z0']], float)

def build_graph(skip=None):
    adj = collections.defaultdict(list)
    for e in EDGES:
        if skip and skip(e): continue
        adj[e['a']].append((e['b'], e)); adj[e['b']].append((e['a'], e))
    return adj

def bfs(adj, src):
    prev = {src: None}; q = collections.deque([src])
    while q:
        u = q.popleft()
        for v, e in adj[u]:
            if v not in prev: prev[v] = (u, e); q.append(v)
    return prev

VIA = {('PLAZA', 'LOBBY'): [(-27.0, -68.6, 0.0), (-27.0, 2.0, 0.0)],
       ('PLAZA', 'PYR_SL'): [], ('PLAZA', 'PYR_SR'): []}

def edge_path(bvh, u, v, e):
    P = _edge_path(bvh, u, v, e)
    if P is None: return None
    if e['type'] == 'door' and 'PLAZA' in (u, v):
        key = (u, v) if (u, v) in VIA else (v, u) if (v, u) in VIA else None
        if key is not None and VIA[key]:
            via = [np.array(p, float) for p in VIA[key]]
            if key == (u, v):   # plaza -> other
                P = [P[0]] + via + P[1:]
            else:               # other -> plaza
                P = P[:-1] + via[::-1] + [P[-1]]
    return P

def _edge_path(bvh, u, v, e):
    """3D points to walk from anchor(u) to anchor(v) through edge e (built a->b, reversed when u is b)"""
    sa, sb = SPACES[e['a']], SPACES[e['b']]
    aa, bb = anchor3(sa), anchor3(sb)
    if e['type'] == 'door':
        d = e['door']; (cx, cy, z0), n = door_world(d); n = np.array(n + (0,), float)
        c = np.array([cx, cy, z0])
        side_a = -1 if np.dot(aa - c, n) < 0 else 1
        pa = c + n * side_a * 1.3; pb = c - n * side_a * 1.3
        pa[2] = sa['z0']; pb[2] = sb['z0']
        P = [aa, pa, c, pb, bb]
    elif e['type'] == 'open' and e['open'].get('room_open'):
        o = e['open']; n = np.array(o['n'] + (0,), float)       # n: corridor -> room
        c = np.array([o['coord'], o['center'], sa['z0']] if o['axis'] == 'x' else [o['center'], o['coord'], sa['z0']], float)
        P = [aa, c - n * 1.3, c + n * 1.3, bb]
    elif e['type'] == 'open':
        P = [aa, bb]
    elif e['type'] == 'stair':
        st = e['stair']; pts = stair_polyline(st)
        f0 = st['flights'][0]; fl = st['flights'][-1]; ex = flight_end(fl)
        s0 = np.array([f0['x'] - f0['dx'] * 0.5, f0['y'] - f0['dy'] * 0.5, f0['z0']])
        s1 = np.array([ex[0] + fl['dx'] * 0.5, ex[1] + fl['dy'] * 0.5, ex[2]])
        s0a = np.array([f0['x'] - f0['dx'] * 1.6, f0['y'] - f0['dy'] * 1.6, f0['z0']])    # inside the approach zone
        s1a = np.array([ex[0] + fl['dx'] * 1.6, ex[1] + fl['dy'] * 1.6, ex[2]])
        P = [aa, s0a, s0] + [np.array(p) for p in pts] + [s1, s1a, bb]
    else:
        return None
    P = [np.array(p, float) for p in P]
    return P if u == e['a'] else P[::-1]

def walk_report(bvh, adj, prev, label):
    rep = dict(label=label, paths=0, ok=0, failed=[], elevator_hops=0)
    for tgt in SPACES:
        if tgt not in prev: continue
        chain = []; c = tgt
        while prev[c] is not None:
            u, e = prev[c]; chain.append((u, c, e)); c = u
        chain = chain[::-1]
        good = True; why = None
        for (u, v, e) in chain:
            P = edge_path(bvh, u, v, e)
            if P is None: rep['elevator_hops'] += 1; continue
            for k, (p0, p1) in enumerate(zip(P[:-1], P[1:])):
                if e['type'] == 'stair' and 0 < k < len(P) - 2:
                    continue   # on the flight itself: every tread / headroom is validated by check_stairs
                segs, err = walk_segment(bvh, p0, p1)
                if segs is None: good = False; why = (u, v, e['type'], tuple(np.round(p0, 2)), tuple(np.round(p1, 2)), err); break
            if not good: break
        rep['paths'] += 1
        if good: rep['ok'] += 1
        else: rep['failed'].append((tgt, why))
    return rep


# ------------------------------------------------------------------ entrances: thresholds, clear width/height, auto-door leaves
ENTRANCES = [('PYR_MAIN', 'PLAZA', 4.0), ('PYR_SL', 'PLAZA', 2.4), ('PYR_SR', 'PLAZA', 2.4), ('LOBBY', 'PLAZA', 6.0)]

def entrance_profile(bvh, x, y, lat, y_from, y_to, step=0.05):
    """walk a capsule-sized corridor (radius 0.35) along +y at lateral offset lat; return max floor step and number of blocked samples"""
    prev = None; maxd = 0.0; worst = None; blocked = []
    t = y_from
    while t <= y_to + 1e-9:
        px, py = x + lat, y + t
        z = floor_z(bvh, px, py, 0.55, 1.0)
        if z is None: z = -9.0
        if prev is not None and abs(z - prev) > maxd: maxd = abs(z - prev); worst = (round(t, 2), round(prev, 3), round(z, 3))
        prev = z
        for k in range(8):
            ang = k * math.pi / 4
            for h in (0.45, 0.95, 1.45, 1.95):
                r = first_hit(bvh, (px, py, z + h), (math.cos(ang), math.sin(ang), 0), 0.35)
                if r is not None: blocked.append((round(t, 2), h, round(math.degrees(ang)), tuple(np.round(r[0], 2))))
        t += step
    return maxd, worst, blocked

def free_width(bvh, x, y, z, cap=14.0):
    r1 = first_hit(bvh, (x, y, z), (1, 0, 0), cap); r2 = first_hit(bvh, (x, y, z), (-1, 0, 0), cap)
    return (r1[0].x if r1 else x + cap) - (r2[0].x if r2 else x - cap)

def check_entrances(bvh):
    out = []
    leaves = {}
    a2 = Acc(); spec.build(); exterior.build_exterior(a2)
    for L in exterior.DOOR_LEAVES: leaves[L['name']] = L
    for sp_id, outside, dw in ENTRANCES:
        d = [d for d in DOORS if d['a'] == outside and d['b'] == sp_id][0]
        cx, cy, ax = d['center'], d['coord'], d['axis']
        pyr = d['glass']
        y_from, y_to = (-4.0, 3.5) if pyr else (-5.0, 4.0)
        res = dict(entrance=sp_id, width=d['width'], height=d['height'], glass=pyr)
        mx = 0.0; nb = 0; ex = None
        lat_list = [0.0, dw / 2 - 0.75, -(dw / 2 - 0.75)]
        for lat in lat_list:
            m, worst, bl = entrance_profile(bvh, cx, cy, lat, y_from, y_to)
            if m > mx: mx, ex = m, worst
            nb += len(bl)
            if bl and 'first_block' not in res: res['first_block'] = bl[0]
        res['max_threshold_step_m'] = round(mx, 4); res['worst_step_at'] = ex; res['blocked_samples'] = nb
        # clear width at several heights: rays shot normal to the (sloping) face / wall plane across the opening
        slope = (PYR_MAIN if sp_id == 'PYR_MAIN' else PYR_SMALL[0])
        if pyr:
            hh = slope['h']; bb_ = slope['base'] / 2
            nout = np.array([0.0, -hh, bb_]); nout /= np.linalg.norm(nout)
        else:
            nout = np.array([0.0, -1.0, 0.0])
        ww = {}
        for zq in (1.0, 1.9, 2.6):
            if zq > d['height'] - 0.2: continue
            yq = cy + (zq * bb_ / hh if pyr else 0.0)
            def blocked_at(xq):
                o = np.array([cx + xq, yq, zq]) + nout * 0.8
                return first_hit(bvh, o, -nout, 1.4) is not None
            lo = 0.0
            while lo > -9 and not blocked_at(lo - 0.05): lo -= 0.05
            hi = 0.0
            while hi < 9 and not blocked_at(hi + 0.05): hi += 0.05
            ww[zq] = round(hi - lo, 2)
        res['clear_width_by_height'] = ww
        res['clear_width_min_m'] = min(ww.values())
        up = first_hit(bvh, (cx, cy + (1.0 if pyr else 0.0), 0.05), (0, 0, 1), 40.0)
        res['clear_height_m'] = round(up[0].z, 2) if up else None
        # auto-door leaves
        key = 'LOBBY' if sp_id == 'LOBBY' else sp_id
        Lf, Rf = leaves.get('AutoDoor_%s_L' % key), leaves.get('AutoDoor_%s_R' % key)
        if Lf and Rf:
            c0 = Lf['cx']
            res['leaf_closed_span'] = [round(float(Lf['x0'] - c0), 3), round(float(Rf['x1'] - c0), 3)]
            res['leaf_closed_covers_opening'] = bool(abs(Lf['x0'] - c0 + dw / 2) < 0.03 and abs(Rf['x1'] - c0 - dw / 2) < 0.03)
            res['leaf_open_clear_width_m'] = round(float((Rf['x0'] + Rf['slide']) - (Lf['x1'] - Lf['slide'])), 2)
            res['leaf_open_outside_opening'] = bool((Lf['x1'] - Lf['slide'] - c0 <= -dw / 2 + 0.02) and (Rf['x0'] + Rf['slide'] - c0 >= dw / 2 - 0.02))
            res['leaf_names'] = [Lf['name'], Rf['name']]
        res['ok'] = bool(mx < 0.05 and nb == 0 and res['clear_width_min_m'] >= (3.0 if sp_id in ('LOBBY', 'PYR_MAIN') else 1.6)
                     and (res['clear_height_m'] is None or res['clear_height_m'] >= (3.0 if sp_id == 'LOBBY' else 1.9))
                     and res.get('leaf_closed_covers_opening', False) and res.get('leaf_open_outside_opening', False))
        out.append(res)
    return out

# ------------------------------------------------------------------ light / emissive fixtures
def check_fixtures():
    acc = Acc(); spec.build(); props.props(acc)
    bad = []; minm = 9.0; minst = 9.0; mindoor = 9.0; n = 0
    by_space = collections.Counter()
    stair_boxes = []
    for st in STAIRS:
        for f in st['flights']:
            for i in range(1, f['n'] + 1):
                r, zt = flight_step_rect(f, i)
                stair_boxes.append((r, zt - abs(f['riser']) - 0.3, zt + HEAD_MIN))
        for r, z in st['landings']: stair_boxes.append((r, z - 0.4, z + HEAD_MIN))
    for fx in props.FIXTURES:
        sp = SPACES[fx['space']]; bb = fx['bbox']; n += 1; by_space[sp['level']] += 1
        x0, y0, x1, y1 = sp['rect']
        marg = min(bb[0] - x0, bb[1] - y0, x1 - bb[3], y1 - bb[4]) if False else min(bb[0] - x0, bb[1] - y0, x1 - bb[3 - 0 + 0] if False else x1 - bb[3], y1 - bb[4])
        minm = min(minm, marg)
        why = []
        if marg < 0.5 - 1e-6: why.append('outside/too close to host walls (%.2f m)' % marg)
        if bb[2] < sp['z0'] - 1e-6 or bb[5] > (0.0 if sp['level'] == 'B1' else sp['z1']) + 1e-6: why.append('outside host height')
        for r, za, zb in stair_boxes:      # stair void incl. 2.2 m headroom column
            if bb[0] < r[2] and bb[3] > r[0] and bb[1] < r[3] and bb[4] > r[1] and bb[2] < zb and bb[5] > za:
                why.append('intersects stair volume / headroom')
                break
        for v in props.stair_voids(bb[2]) + props.door_voids(sp):
            if props._hit(bb, v): why.append('within 0.5 m of a stair opening / doorway'); break
        # distance to stair openings (plan) for the report
        for r, za, zb in stair_boxes:
            if za < bb[5] + 2.4 and zb > bb[2] - 0.5:
                dx = max(r[0] - bb[3], bb[0] - r[2], 0); dy = max(r[1] - bb[4], bb[1] - r[3], 0); minst = min(minst, math.hypot(dx, dy))
        if why: bad.append(dict(space=fx['space'], bbox=[round(x, 2) for x in bb], why=why))
    return dict(fixtures=n, by_level=dict(by_space), violations=len(bad), min_margin_to_host_walls_m=round(minm, 2),
                min_plan_distance_to_stair_m=round(minst, 2), details=bad[:10])

def check_open_rooms(bvh, opened=None):
    """small gallery rooms with the door wall removed: nothing may remain on the old door-wall line (wall, lintel, frame,
    door leaf), floors must be continuous and step-free across it; also count the kept partitions usable for art."""
    opened = spec.OPENED if opened is None else opened
    bad = []; n_rays = 0
    for o in opened:
        n = np.array(o['n'] + (0,), float); z0 = BAND_Z[o['band']][0]
        zc = SPACES[o['room']]['z1'] - SLAB
        for k in range(int((o['a1'] - o['a0'] - 0.8) / 0.5) + 1):
            u = o['a0'] + 0.4 + 0.5 * k
            c = np.array([o['coord'], u, z0] if o['axis'] == 'x' else [u, o['coord'], z0], float)
            for h in (0.15, 1.0, 2.0, 3.2, 3.5, 5.0, zc - z0 - 0.3):
                n_rays += 1
                r = first_hit(bvh, c - n * 0.9 + np.array([0, 0, h]), n, 1.8)
                if r is not None: bad.append((o['room'], round(u, 2), h, 'remnant', tuple(np.round(r[0], 2)))); break
            for s_ in (-0.5, -0.05, 0.05, 0.5):
                p = c + n * s_; z = floor_z(bvh, p[0], p[1], z0 + 1.0, 2.0)
                if z is None or abs(z - z0) > 0.01: bad.append((o['room'], round(u, 2), s_, 'floor', z)); break
    # partitions: room side walls perpendicular to the removed door wall
    rooms = {o['room']: o for o in opened}
    parts = {}
    for o in opened:
        r = SPACES[o['room']]['rect']
        if o['axis'] == 'x': sides = [('y', r[1]), ('y', r[3])]; depth = r[2] - r[0]
        else: sides = [('x', r[0]), ('x', r[2])]; depth = r[3] - r[1]
        for ax, c in sides:
            key = (ax, round(c, 3), o['band'], round(o['coord'], 3))
            parts.setdefault(key, []).append((o['room'], depth))
    shared = {k: v for k, v in parts.items() if len(v) == 2}
    single = {k: v for k, v in parts.items() if len(v) == 1}
    net = lambda d: d - arch.T_EXT / 2                       # door-wall line -> inner face of the exterior wall
    faces_len = sum(net(d) for v in parts.values() for _, d in v)
    return dict(opened_walls=len(opened), rays=n_rays, ok=(len(bad) == 0), failed_rooms=len(set((b[0]) for b in bad)), fails=bad[:10],
                partitions_room_to_room=len(shared), side_walls_room_to_hall=len(single),
                art_wall_faces=sum(len(v) for v in parts.values()), art_wall_length_m=round(faces_len, 1))

def check_tower_open(bvh):
    """t27u: every wall removed in / around the corner towers is really gone (rays across the old wall line at 7 heights find
    nothing, floor continuous and step-free), and what must stay is still there: stair-shaft + elevator-cab enclosures, exterior walls"""
    r = check_open_rooms(bvh, spec.TOWER_OPENED)
    out = dict(removed_walls=len(spec.TOWER_OPENED), rays=r['rays'], ok=r['ok'], fails=r['fails'],
               by_tower={q: sum(1 for o in spec.TOWER_OPENED if o['tower'] == q) for q in ('NW', 'NE', 'SW', 'SE')},
               by_kind=dict(collections.Counter(o['kind'] for o in spec.TOWER_OPENED)))
    kept_bad = []
    for sp in SPACES.values():
        if sp['kind'] not in spec.TOWER_KEEP or not sp['zone'].startswith('pav') or sp['level'] not in ('L1', 'L2', 'L3'): continue
        x0, y0, x1, y1 = sp['rect']; z = sp['z0'] + 1.2; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for d, (px, py) in (((1, 0), (x1, cy)), ((-1, 0), (x0, cy)), ((0, 1), (cx, y1)), ((0, -1), (cx, y0))):
            # ray from inside the space towards each enclosure wall: must hit within 0.6 m of the wall line (door gaps avoided:
            # probe at 3 offsets, one hit is enough)
            ok = False
            for off in (-0.3, 0.0, 0.3) if d[0] else (-0.3, 0.0, 0.3):
                q = ((x1 - x0) * off, 0) if d[0] == 0 else (0, (y1 - y0) * off)
                o = np.array([cx + q[0], cy + q[1], z]); dist = abs((px - cx) if d[0] else (py - cy))
                h = first_hit(bvh, o, np.array([d[0], d[1], 0.0]), dist + 0.6)
                if h is not None and abs(h[3] - dist) < 0.6: ok = True; break
            if not ok: kept_bad.append((sp['id'], d))
    out['kept_enclosures_checked'] = sum(1 for sp in SPACES.values() if sp['kind'] in spec.TOWER_KEEP and sp['zone'].startswith('pav') and sp['level'] in ('L1', 'L2', 'L3'))
    out['kept_enclosure_fails'] = kept_bad
    out['ok'] = out['ok'] and not kept_bad
    art.faces(); out['slot_faces_dropped'] = len(art.DROPPED)
    return out

def check_slots(bvh, slots=None):
    """display slots: whole frame on a wall face (corner/edge rays hit the wall right behind it), nothing in front of it,
    clear of windows / doors / opened door-wall lines / face ends, no two slots overlapping"""
    slots = art.build_slots() if slots is None else slots
    hw, hh = art.SLOT_W / 2, art.SLOT_H / 2
    bad = []
    for s in slots:
        p = np.array(s['pos'], float); n = np.array(s['normal'], float)
        t = np.array([-n[1], n[0], 0.0]); why = []
        for du in (-hw + 0.03, 0.0, hw - 0.03):
            for dz in (-hh + 0.03, 0.0, hh - 0.03):
                o = p + t * du + np.array([0, 0, dz]) + n * 0.3
                r = first_hit(bvh, o, -n, 0.3 + art.DEPTH + 0.03)
                if r is None or abs((r[0] - Vector(o)).length - (0.3 + art.DEPTH)) > 0.015: why.append(('off_wall', du, dz)); break
            if why: break
        r = first_hit(bvh, p + n * 0.01, n, 1.0)
        if r is not None: why.append(('blocked_in_front', round(r[3], 2)))
        u0, u1 = s['u'] - hw, s['u'] + hw; z0 = s['pos'][2] - hh; z1 = s['pos'][2] + hh
        for w in arch.WINDOW_CUTS:
            if w['axis'] == s['wall_axis'] and abs(w['coord'] - s['wall_coord']) < 0.5 and w['a0'] < u1 and w['a1'] > u0 and w['z0'] < z1 and w['z1'] > z0: why.append('window')
        for d in DOORS:
            if d['axis'] == s['wall_axis'] and d['band'] == s['band'] and abs(d['coord'] - s['wall_coord']) < 0.5 and d['center'] - d['width'] / 2 - 0.3 < u1 and d['center'] + d['width'] / 2 + 0.3 > u0: why.append(('door', d['a'], d['b']))
        for o in spec.OPENED + spec.TOWER_OPENED:
            if o['axis'] != s['wall_axis'] and o['band'] == s['band'] and u0 - 0.3 < o['coord'] < u1 + 0.3 and o['a0'] - 1e-6 <= s['wall_coord'] <= o['a1'] + 1e-6: why.append('opened_line')
        if why: bad.append((s['id'], s['room'], why[:3]))
    ov = 0
    for i, a in enumerate(slots):
        for b in slots[i + 1:]:
            if a['wall_axis'] == b['wall_axis'] and abs(a['face_coord'] - b['face_coord']) < 1e-3 and a['band'] == b['band'] and a['normal'] == b['normal'] and abs(a['u'] - b['u']) < art.SLOT_W + 0.2: ov += 1
    return dict(slots=len(slots), ok=len(slots) - len(bad), overlaps=ov, size=[art.SLOT_W, art.SLOT_H], fails=bad[:10])

def check_floor_props():
    """no small models / plinths on room floors any more (only ceiling lights, the atrium hologram and the L4 mech cabinet remain)"""
    spec.build(); a = Acc(); props.props(a)
    floors = [-6.0, 0.0, 8.0, 16.0, 24.0]
    left = collections.Counter(); bad_mats = []
    for m, (V, F) in a.g.get('Props', {}).items():
        if m in props.FLOOR_PROP_MATS: bad_mats.append(m)
        Vn = np.array(V) if V else np.zeros((0, 3))
        for f in F:
            zs = Vn[list(f), 2]
            if any(abs(zs.min() - fl) < 0.02 for fl in floors) and zs.max() - zs.min() < 3.0: left[m] += 1
    ok = not bad_mats and set(left) <= {'frame_dark', 'gold'}     # frame_dark / gold faces on a floor = door jambs + the L4 mech cabinet
    return dict(ok=ok, exhibit_materials_left=bad_mats, floor_touching_prop_faces=dict(left), removed=dict(props.REMOVED))

def main():
    bvh, acc = build_bvh()
    res = dict()
    # graph reachability
    entrance = 'PLAZA'
    adj = build_graph()
    prev = bfs(adj, entrance)
    unreached = [s for s in SPACES if s not in prev]
    # reachable only via the pyramid entrance: drop the direct lobby door
    adj_p = build_graph(skip=lambda e: e['type'] == 'door' and e['door']['kind'] == 'main_door')
    prev_p = bfs(adj_p, 'PYR_MAIN')
    unreached_p = [s for s in SPACES if s not in prev_p and s != 'PLAZA']
    # without elevators
    adj_ne = build_graph(skip=lambda e: e['type'] == 'elevator' or (e['type'] == 'door' and e['door']['kind'] == 'main_door'))
    prev_ne = bfs(adj_ne, 'PYR_MAIN')
    unreached_ne = [s for s in SPACES if s not in prev_ne and s != 'PLAZA']
    res['spaces'] = len(SPACES)
    by_level = collections.Counter(s['level'] for s in SPACES.values())
    res['spaces_by_level'] = dict(by_level)
    res['edges'] = collections.Counter(e['type'] for e in EDGES)
    res['reachable_from_plaza'] = len(SPACES) - len(unreached); res['unreached_from_plaza'] = unreached
    res['reachable_from_pyramid_entrance_only'] = len(SPACES) - len(unreached_p) - 1; res['unreached_pyramid_only'] = unreached_p
    res['reachable_stairs_only_no_elevator'] = len(SPACES) - len(unreached_ne) - 1; res['unreached_no_elevator'] = unreached_ne
    # geometry checks
    doors = check_doors(bvh)
    res['doors'] = len(doors)
    res['doors_cut_ok'] = sum(1 for d in doors if d['cut'])
    res['doors_wall_beside_ok'] = sum(1 for d in doors if d['wall_beside'])
    res['doors_lintel_ok'] = sum(1 for d in doors if d['lintel'] in (True, None))
    res['doors_floor_ok'] = sum(1 for d in doors if d['floor_both_sides'] or d['glass'] or d['kind'] == 'main_door')
    res['door_failures'] = [d for d in doors if not (d['cut'] and d['wall_beside'])][:12]
    stairs = check_stairs(bvh)
    res['stairs'] = len(stairs); res['stairs_ok'] = sum(1 for s in stairs if s['ok'])
    res['max_riser_m'] = max(s['max_riser'] for s in stairs); res['min_tread_m'] = min(s['min_tread'] for s in stairs)
    res['min_headroom_m'] = round(min(s['min_head'] for s in stairs), 3); res['total_steps_checked'] = sum(s['steps'] for s in stairs)
    res['stair_failures'] = [s for s in stairs if not s['ok']][:8]
    res['entrances'] = check_entrances(bvh)
    res['windows'] = check_windows(bvh, acc)
    res['open_rooms'] = check_open_rooms(bvh)
    res['tower_open'] = check_tower_open(bvh)
    res['slots'] = check_slots(bvh)
    res['floor_props'] = check_floor_props()
    res['panes'] = check_panes(acc)
    wells = check_stair_wells(bvh)
    res['stair_wells_checked'] = len(wells); res['stair_wells_ok'] = sum(1 for w in wells if w['ok'])
    res['stair_wells_min_head_m'] = min(w['min_head'] for w in wells)
    res['stair_wells_failing'] = [(w['id'], w['fails']) for w in wells if not w['ok']]
    res['stair_wells_top_levels'] = sorted(set(w['top_z'] for w in wells))
    import stair_rules
    rows, holes = stair_rules.audit(bvh, acc)
    res['stair_rules_rows'] = rows; res['stair_rules_holes'] = holes
    res['stair_rules_checked'] = len(rows)
    res['stair_rules_violations'] = sum(len(r['issues']) for r in rows) + sum(len(h['unguarded']) for h in holes)
    res['stair_rules_failing'] = [(r['id'], r['issues']) for r in rows if r['issues']] + [('HOLE', h['rect'], h['unguarded']) for h in holes if h['unguarded']]
    res['fixtures'] = check_fixtures()
    # floor under every anchor
    nof = []
    for sp in SPACES.values():
        if sp['kind'] == 'outdoor' or sp['level'] == 'L4' and False: continue
        a = anchor3(sp)
        z = floor_z(bvh, a[0], a[1], a[2] + 1.0, 3.0)
        if z is None or abs(z - a[2]) > 0.05: nof.append((sp['id'], z, a[2]))
    res['anchors_without_floor'] = nof
    # headroom at anchors (clear height above floor >= 2.2)
    lowhead = []
    for sp in SPACES.values():
        if sp['kind'] in ('outdoor',): continue
        a = anchor3(sp); hit = first_hit(bvh, (a[0], a[1], a[2] + 0.05), (0, 0, 1), 40.0)
        if hit is not None and hit[0].z - a[2] < HEAD_MIN: lowhead.append((sp['id'], round(hit[0].z - a[2], 2)))
    res['anchors_low_headroom'] = lowhead
    # walking simulation
    w1 = walk_report(bvh, adj, prev, 'from PLAZA (all links)')
    w2 = walk_report(bvh, adj_p, prev_p, 'from pyramid entrance only (no lobby door, with elevators)')
    w3 = walk_report(bvh, adj_ne, prev_ne, 'pyramid entrance only, stairs only (no elevators)')
    res['walk'] = [w1, w2, w3]
    res['bvh_triangles'] = len(bvh.__class__.__name__) and None
    json.dump(res, open(os.path.join(OUT, 'connectivity_report.json'), 'w'), indent=1, default=str)
    return res

if __name__ == '__main__':
    r = main()
    for k, v in r.items():
        if k in ('door_failures', 'stair_failures', 'walk', 'entrances', 'fixtures', 'stair_rules_rows', 'stair_rules_holes', 'stair_wells_failing'): continue
        print(k, ':', v)
    for w in r['walk']:
        print(w['label'], 'paths', w['paths'], 'ok', w['ok'], 'failed', len(w['failed']), 'elev hops', w['elevator_hops'])
        for f in w['failed'][:6]: print('   FAIL', f)
    for e in r['entrances']: print('ENTRANCE', e)
    print('FIXTURES', r['fixtures'])
    for f in r['stair_wells_failing']: print('STAIR WELL FAIL', f)
    import stair_rules
    print('\n'.join(stair_rules.summarize(r['stair_rules_rows'], r['stair_rules_holes'])))
    for f in r['door_failures'][:8]: print('DOOR', f)
    for f in r['stair_failures'][:5]: print('STAIR', f)
