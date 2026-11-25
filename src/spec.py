"""Topology spec for the Cyber Louvre: masses, spaces, doors, stairs. Pure python.
Coordinates: x east, y north, z up. Building 180 (x) x 120 (y). South = -y (open courtyard side, pyramids)."""
import math
from geom import rect_minus

SLAB = 0.4
LEVELS = {'B1': -8.0, 'L1': 0.0, 'L2': 10.0, 'L3': 20.0, 'L4': 30.0}
BAND_Z = {'B1': (-8.0, 0.0), 'L1': (0.0, 10.0), 'L2': (10.0, 20.0), 'L3': (20.0, 30.0), 'L4': (30.0, 40.0)}
ORDER = ['B1', 'L1', 'L2', 'L3', 'L4']
RISER_MAX = 0.2
HEAD_MIN = 2.2
HEAD_STAIR = 2.4     # stair headroom target (public + grand)

# ------------------------------------------------------------------ exterior masses (footprint, wall height)
# name, rect(x0,y0,x1,y1), wall height, kind
def mirror_rect(r, sx, sy):
    x0, y0, x1, y1 = r
    if sx == 1: x0, x1 = -x1, -x0
    if sy == -1: y0, y1 = -y1, -y0
    return (x0, y0, x1, y1)

def mirror_pt(x, y, sx, sy):
    return (x if sx == -1 else -x, y if sy == 1 else -y)

QN = {(-1, 1): 'NW', (1, 1): 'NE', (-1, -1): 'SW', (1, -1): 'SE'}

PAV_R = (-80, 34, -54, 60)
WING_R = (-74, -34, -54, 34)
BUMP_R = (-90, -17, -74, 17)
NWING_R = (-54, 30, -14, 50)
CENTER_S = (-14, 8, 14, 32)
CENTER_N = (-14, 32, 14, 60)

MASSES = []
for (sx, sy), q in QN.items():
    MASSES.append(dict(name='PAV_' + q, rect=mirror_rect(PAV_R, sx, sy), h=30, kind='pav', q=q))
for sx in (-1, 1):
    s = 'W' if sx == -1 else 'E'
    MASSES.append(dict(name='WING_' + s, rect=mirror_rect(WING_R, sx, 1), h=30, kind='wing', q=s))
    MASSES.append(dict(name='BUMP_' + s, rect=mirror_rect(BUMP_R, sx, 1), h=30, kind='bump', q=s))
    MASSES.append(dict(name='NWING_' + s, rect=mirror_rect(NWING_R, sx, 1), h=30, kind='nwing', q=s))
MASSES.append(dict(name='CENTER_S', rect=CENTER_S, h=40, kind='center', q='C'))
MASSES.append(dict(name='CENTER_N', rect=CENTER_N, h=40, kind='drum', q='C'))

PYR_MAIN = dict(c=(0, -48), base=36, h=21)
PYR_SMALL = [dict(c=(-37, -52), base=12, h=7), dict(c=(37, -52), base=12, h=7)]
DOME = dict(c=(0, 46), r=14, h=13, z0=40)

# ------------------------------------------------------------------ spaces
SPACES = {}
DOORS = []      # cut openings in walls
OPENS = []      # wall-less boundary intervals
EDGES = []      # graph edges: dict(type, a, b, ...)
STAIRS = []
HOLES = {}      # z -> list of rects
HOLE_META = []  # dict(z, rect, access) for guardrails around slab openings
OPEN_ROOMS = True   # small gallery rooms off the wing / north-wing corridors: whole door wall removed (open alcove bays)
OPENED = []         # registry of removed door walls: dict(room, corr, axis, coord, a0, a1, band, n)
TOWER_OPEN = True   # corner towers (pavilions) L1-L3: interior hall/lobby wall + every wall to the adjacent rooms/corridors removed
TOWER_OPEN_PARTITIONS = False   # also remove the adjacent rooms' partitions to the next (non-adjacent) rooms (kept: art walls, t23u)
TOWER_OPENED = []   # registry of walls removed by open_towers(): dict(room, corr, axis, coord, a0, a1, band, n, kind, a, b)
TOWER_KEEP = ('stair', 'elevator')   # stair shafts + elevator cabs keep their enclosure

def add_space(id, level, rect, **kw):
    z0 = LEVELS[level]
    h = kw.pop('h', 10.0 if level not in ('B1', 'L4') else (8.0 if level == 'B1' else 5.0))
    sp = dict(id=id, level=level, rect=tuple(rect), z0=z0, z1=z0 + h, bands=[level], kind='room',
              floor=None, walls=True, ceil=True, anchor=None, zone='')
    sp.update(kw)
    if sp['floor'] is None: sp['floor'] = [sp['rect']]
    if sp['anchor'] is None:
        sp['anchor'] = ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
    assert id not in SPACES, id
    SPACES[id] = sp
    return sp

def add_door(a, b, axis, coord, center, width, height, band, glass=False, kind='door'):
    d = dict(a=a, b=b, axis=axis, coord=coord, center=center, width=width, height=height, band=band, glass=glass, kind=kind)
    DOORS.append(d)
    EDGES.append(dict(type='door', a=a, b=b, door=d))
    return d

def add_open(a, b, axis, coord, a0, a1, bands, check_z=True):
    o = dict(a=a, b=b, axis=axis, coord=coord, a0=a0, a1=a1, bands=bands)
    OPENS.append(o)
    EDGES.append(dict(type='open', a=a, b=b, open=o, check_z=check_z))
    return o

def flight(x, y, z0, dx, dy, w, n, riser, tread):
    return dict(x=x, y=y, z0=z0, dx=dx, dy=dy, w=w, n=n, riser=riser, tread=tread)

def flight_step_rect(f, i):
    """i = 1..n ; returns rect (x0,y0,x1,y1) and top z of step i"""
    s0, s1 = (i - 1) * f['tread'], i * f['tread']
    dx, dy = f['dx'], f['dy']
    # along-axis extents and cross extents
    if abs(dx) > 0.5:
        xa, xb = f['x'] + dx * s0, f['x'] + dx * s1
        r = (min(xa, xb), f['y'] - f['w'] / 2, max(xa, xb), f['y'] + f['w'] / 2)
    else:
        ya, yb = f['y'] + dy * s0, f['y'] + dy * s1
        r = (f['x'] - f['w'] / 2, min(ya, yb), f['x'] + f['w'] / 2, max(ya, yb))
    return r, f['z0'] + i * f['riser']

def flight_end(f):
    s = f['n'] * f['tread']
    return (f['x'] + f['dx'] * s, f['y'] + f['dy'] * s, f['z0'] + f['n'] * f['riser'])

def mirror_flight(f, sx, sy):
    x, y = mirror_pt(f['x'], f['y'], sx, sy)
    dx = f['dx'] * (1 if sx == -1 else -1)
    dy = f['dy'] * (1 if sy == 1 else -1)
    g = dict(f); g.update(x=x, y=y, dx=dx, dy=dy)
    return g

def add_stair(id, a, b, flights, landings, kind='stair', hole_z=None):
    st = dict(id=id, a=a, b=b, flights=flights, landings=landings, kind=kind)
    st['start'] = (flights[0]['x'], flights[0]['y'], flights[0]['z0'])
    st['end'] = flight_end(flights[-1])
    STAIRS.append(st)
    EDGES.append(dict(type='stair', a=a, b=b, stair=st))
    return st

def add_headroom_holes(landings, zslab, margin=0.2):
    """open the slab above a landing whose clearance would otherwise be under HEAD_STAIR.
    The opening joins the flight hole; sides with no floor outside do not need a rail."""
    limit = zslab - SLAB - HEAD_STAIR
    for r, z in landings:
        if z > limit - 0.02:
            h = (r[0] - margin, r[1] - margin, r[2] + margin, r[3] + margin)
            HOLES.setdefault(zslab, []).append(h)
            HOLE_META.append(dict(z=zslab, rect=h, access='S'))

def add_hole_for_flight(f, zslab_level, thresh=-(SLAB + HEAD_STAIR + 0.15), margin=0.25):
    """hole in slab at z=zslab_level over the steps whose tread top is higher than thresh (below slab)."""
    rects = []
    for i in range(1, f['n'] + 1):
        r, zt = flight_step_rect(f, i)
        if zt > zslab_level + thresh:
            rects.append(r)
    if not rects: return
    x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects); x1 = max(r[2] for r in rects); y1 = max(r[3] for r in rects)
    if abs(f['dy']) > 0.5:
        h = (x0, y0 - (margin if f['dy'] > 0 else 0), x1, y1 + (margin if f['dy'] < 0 else 0))
    else:
        h = (x0 - (margin if f['dx'] > 0 else 0), y0, x1 + (margin if f['dx'] < 0 else 0), y1)
    HOLES.setdefault(zslab_level, []).append(h)
    # access side = the side from which people step onto / off the flight at this slab level
    e = flight_end(f)
    if abs(e[2] - zslab_level) < 0.01: sgn, dx, dy = 1, f['dx'], f['dy']
    else: sgn, dx, dy = -1, f['dx'], f['dy']
    if abs(dy) > 0.5: side = 'N' if dy * sgn > 0 else 'S'
    else: side = 'E' if dx * sgn > 0 else 'W'
    HOLE_META.append(dict(z=zslab_level, rect=h, access=side))
    return h

def straight_flights(x, y0, z0, dy, w, total_n, riser, tread, nf, ldepth):
    """one straight stair run split into nf flights (<=18 risers each) with straight landings of depth ldepth"""
    n = total_n // nf; assert n * nf == total_n and n <= 18
    flights, landings = [], []
    y = y0; z = z0
    for k in range(nf):
        f = flight(x, y, z, 0, dy, w, n, riser, tread); flights.append(f)
        e = flight_end(f)
        if k < nf - 1:
            ya = e[1]
            landings.append(((x - w / 2, min(ya, ya + dy * ldepth), x + w / 2, max(ya, ya + dy * ldepth)), e[2]))
            y = ya + dy * ldepth; z = e[2]
    return flights, landings

# ------------------------------------------------------------------ build all spaces
def room_link(cid, rid, axis, coord, center, width, height, band):
    """corridor <-> small gallery room: a door (old design) or, with OPEN_ROOMS, the whole door wall removed"""
    if not OPEN_ROOMS:
        return add_door(cid, rid, axis, coord, center, width, height, band)
    r = SPACES[rid]['rect']
    a0, a1 = (r[1], r[3]) if axis == 'x' else (r[0], r[2])
    rc = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    n = (1 if rc[0] > coord else -1, 0) if axis == 'x' else (0, 1 if rc[1] > coord else -1)   # corridor -> room
    o = add_open(cid, rid, axis, coord, a0, a1, [band])
    o['room_open'] = True; o['center'] = center; o['n'] = n
    OPENED.append(dict(room=rid, corr=cid, axis=axis, coord=coord, a0=a0, a1=a1, band=band, n=n))
    return o

def shared_edge(r1, r2, minlen=0.5):
    """two touching (non-overlapping) rects -> (axis, coord, a0, a1) of their common wall segment, else None"""
    for axis, (c1a, c1b, c2a, c2b, u1, u2) in (('x', (r1[2], r1[0], r2[0], r2[2], (r1[1], r1[3]), (r2[1], r2[3]))),
                                              ('y', (r1[3], r1[1], r2[1], r2[3], (r1[0], r1[2]), (r2[0], r2[2])))):
        for c in (c1a, c1b):
            if (abs(c - c2a) < 1e-6 and c == c1a) or (abs(c - c2b) < 1e-6 and c == c1b):
                a0, a1 = max(u1[0], u2[0]), min(u1[1], u2[1])
                if a1 - a0 >= minlen: return axis, c, a0, a1
    return None

def _covered(axis, coord, a0, a1, band):
    return any(o['axis'] == axis and abs(o['coord'] - coord) < 1e-3 and band in o['bands'] and o['a0'] <= a0 + 1e-6 and o['a1'] >= a1 - 1e-6
               for o in OPENS)

def open_towers():
    """t27u: inside each corner tower (pavilion) the hall <-> core-lobby wall is removed, and so is every wall between the tower
    (hall + lobby) and the rooms / corridors next to it, plus the walls between those adjacent rooms themselves -> one open,
    walkable floor per tower and storey.  Kept: exterior walls (windows), the stair-shaft enclosure, the elevator cab, slabs."""
    for q in QN.values():
        for lv in ('L1', 'L2', 'L3'):
            tower = ['PAV_%s_HALL_%s' % (q, lv), 'PAV_%s_LOB_%s' % (q, lv)]
            cands = [s for s in SPACES.values() if lv in s['bands'] and s['walls'] and s['id'] not in tower and s['kind'] not in TOWER_KEEP]
            pairs = [(tower[0], tower[1], 'tower_interior')]
            adj = []
            for t in tower:
                for s in cands:
                    if shared_edge(SPACES[t]['rect'], s['rect']):
                        pairs.append((t, s['id'], 'tower_to_' + s['kind'])); adj.append(s['id'])
            adj = sorted(set(adj))
            rooms = [a for a in adj if SPACES[a]['kind'] == 'gallery']
            for i, a in enumerate(rooms):          # neighbour room <-> neighbour room (not corridor <-> room: that is OPEN_ROOMS' job)
                for b in rooms[i + 1:]:
                    if shared_edge(SPACES[a]['rect'], SPACES[b]['rect']): pairs.append((a, b, 'adjacent_to_adjacent'))
            if TOWER_OPEN_PARTITIONS:
                for a in rooms:
                    for s in cands:
                        if s['id'] not in adj and s['id'] not in tower and shared_edge(SPACES[a]['rect'], s['rect']):
                            pairs.append((a, s['id'], 'adjacent_partition'))
            for a, b, kind in pairs:
                axis, coord, a0, a1 = shared_edge(SPACES[a]['rect'], SPACES[b]['rect'])
                if _covered(axis, coord, a0, a1, lv): continue          # already open (corridor <-> open gallery bay)
                # a door in that wall goes with it
                for d in [d for d in DOORS if {d['a'], d['b']} == {a, b} and d['band'] == lv]:
                    DOORS.remove(d)
                    for e in [e for e in EDGES if e.get('door') is d]: EDGES.remove(e)
                ra, rb = SPACES[a]['rect'], SPACES[b]['rect']
                ca = ((ra[0] + ra[2]) / 2, (ra[1] + ra[3]) / 2)
                n = (1 if ca[0] < coord else -1, 0) if axis == 'x' else (0, 1 if ca[1] < coord else -1)   # a -> b
                o = add_open(a, b, axis, coord, a0, a1, [lv])
                o['room_open'] = True; o['center'] = (a0 + a1) / 2; o['n'] = n; o['tower'] = q
                TOWER_OPENED.append(dict(room=b, corr=a, a=a, b=b, axis=axis, coord=coord, a0=a0, a1=a1, band=lv, n=n, kind=kind, tower=q))

def build():
    SPACES.clear(); DOORS.clear(); OPENS.clear(); EDGES.clear(); STAIRS.clear(); HOLES.clear(); HOLE_META.clear(); OPENED.clear()
    TOWER_OPENED.clear()
    L3 = ['L1', 'L2', 'L3']

    # ---------------- outdoor plaza (courtyard)
    pl_rects = [(-54, -70, 54, 8), (-54, 8, -14, 30), (14, 8, 54, 30)]
    add_space('PLAZA', 'L1', (-54, -70, 54, 8), kind='outdoor', walls=False, ceil=False, floor=pl_rects, h=40,
              zone='plaza', anchor=(0, -68.6))
    # ---------------- pyramids
    pm = PYR_MAIN
    add_space('PYR_MAIN', 'L1', (-18, -66, 18, -30), kind='pyramid', walls=False, ceil=False, floor=[], h=21,
              zone='pyr', anchor=(0, -60))
    for k, ps in enumerate(PYR_SMALL):
        cx, cy = ps['c']
        add_space('PYR_S%s' % ('L' if cx < 0 else 'R'), 'L1', (cx - 6, cy - 6, cx + 6, cy + 6), kind='pyramid', walls=False,
                  ceil=False, floor=[], h=7, zone='pyr', anchor=(cx, cy - 4.5))
    # ---------------- basement concourse
    add_space('B1_HALL', 'B1', (-46, -58, 46, -38), kind='concourse', ceil=False, zone='b1', anchor=(12, -47))
    add_space('B1_SPINE', 'B1', (-5, -38, 5, 24), kind='concourse', ceil=False, zone='b1', anchor=(0, -20))
    add_open('B1_HALL', 'B1_SPINE', 'y', -38, -5, 5, ['B1'])
    # plaza <-> pyramids doors (glass)
    add_door('PLAZA', 'PYR_MAIN', 'y', -66, 0, 4.0, 4.5, 'L1', glass=True)
    for ps in PYR_SMALL:
        cx, cy = ps['c']
        add_door('PLAZA', 'PYR_S%s' % ('L' if cx < 0 else 'R'), 'y', cy - 6, cx, 2.4, 2.8, 'L1', glass=True)
    # pyramid stairs down. B1 storey is 8 m; keep the 1/6 m riser -> 48 risers.
    rise_b1 = LEVELS['L1'] - LEVELS['B1']
    riser_b1 = rise_b1 / 48
    # main pyramid -> B1: 3 flights x 16 + two 3 m landings, 3.4 m wide, continuing into the spine
    # end inside B1_HALL (y=-40), so the walk to the hall anchor stays on the hall floor
    fms, lms = straight_flights(0, -57.5, 0.0, 1, 3.4, 48, -riser_b1, 0.3, 3, 3.0)
    add_stair('S_PM', 'PYR_MAIN', 'B1_HALL', fms, lms)
    for f in fms: add_hole_for_flight(f, 0.0)
    add_headroom_holes(lms, 0.0)
    for ps in PYR_SMALL:
        cx, cy = ps['c']; sgn = -1 if cx < 0 else 1
        side = 'L' if cx < 0 else 'R'
        # 4 x 12 U, 2.0 m wide. North run stays inside the B1 hall (hall goes to y=-38).
        w, n, tr = 2.0, 12, 0.30
        xA = cx - 2.4 if sgn == -1 else cx + 2.4
        xB = cx + 2.4 if sgn == -1 else cx - 2.4
        y0 = cy - 1.0                               # same south clearance the 2-flight stair had
        fl, ld = [], []
        a1 = flight(xA, y0, 0.0, 0, 1, w, n, -riser_b1, tr); e = flight_end(a1); fl.append(a1)
        ld.append(((xA - 1.0, e[1], xA + 1.0, e[1] + 1.2), e[2]))
        a2 = flight(xA, e[1] + 1.2, e[2], 0, 1, w, n, -riser_b1, tr); e = flight_end(a2); fl.append(a2)
        xs = sorted([xA - 1.0, xA + 1.0, xB - 1.0, xB + 1.0])
        ld.append(((xs[0], e[1], xs[-1], e[1] + 2.4), e[2]))
        b1 = flight(xB, e[1], e[2], 0, -1, w, n, -riser_b1, tr); eb = flight_end(b1); fl.append(b1)
        ld.append(((xB - 1.0, eb[1] - 1.2, xB + 1.0, eb[1]), eb[2]))
        b2 = flight(xB, eb[1] - 1.2, eb[2], 0, -1, w, n, -riser_b1, tr); fl.append(b2)
        add_stair('S_PS' + side, 'PYR_S' + side, 'B1_HALL', fl, ld)
        for f in fl: add_hole_for_flight(f, 0.0)
        add_headroom_holes(ld, 0.0)

    # ---------------- central block: lobby + atrium (tall)
    tall = ['L1', 'L2', 'L3', 'L4']
    add_space('LOBBY', 'L1', (-14, 8, 14, 32), kind='lobby', bands=tall, h=40, zone='C', anchor=(-6, 24))
    add_space('ATRIUM', 'L1', (-14, 32, 14, 60), kind='atrium', bands=tall, h=40, ceil=False, zone='C', anchor=(0, 44))
    add_open('LOBBY', 'ATRIUM', 'y', 32, -14, 14, tall)
    add_door('PLAZA', 'LOBBY', 'y', 8, 0, 6.0, 6.0, 'L1', kind='main_door')
    # 8 m at 1/6 m = 3 x 16. Finish at the spine's north edge (y=23.6): past y=24 the
    # earth pad rises to z=-0.42 and would bury the upper treads.
    _lob_run = 3 * 16 * 0.3 + 2 * 3.0
    fls, lls = straight_flights(0, 23.6 - _lob_run, LEVELS['B1'], 1, 3.4, 48, riser_b1, 0.3, 3, 3.0)
    add_stair('S_LOBBY', 'B1_SPINE', 'LOBBY', fls, lls)
    for f in fls: add_hole_for_flight(f, 0.0)
    add_headroom_holes(lls, 0.0)
    # grand stairs. 10 m at 1/6 m riser = 60 risers. L1->L2 is a straight 4 x 15 tucked against the
    # lobby side walls (centre x=±11.95) so the whole 3.2 m width lands on the side ring, not the void.
    # L2->L3 stays the central U, lengthened to 4 x 15; its south end stays 2 m clear of the side stairs.
    riser = (LEVELS['L2'] - LEVELS['L1']) / 60
    YG = 25.0                                   # south edge of the L2 / L3 gallery bridges
    add_space('GL2', 'L2', (-14, YG, 14, 32), kind='platform', walls=False, ceil=False, zone='C', anchor=(0, 28))
    add_space('GL3', 'L3', (-14, YG, 14, 32), kind='platform', walls=False, ceil=False, zone='C', anchor=(0, 28))
    for sx in (-1, 1):
        s = 'W' if sx == -1 else 'E'
        # 3 x 15 north, then a quarter-turn and 15 toward the centre. The run stops
        # south of y=32 so the bridge-to-ring walk is not cut by the stair opening.
        w = 3.0
        x = sx * 10.9
        y, z = 12.6, LEVELS['L1']
        f1s, l1s = [], []
        for k in range(3):
            f = flight(x, y, z, 0, 1, w, 15, riser, 0.3); f1s.append(f); e = flight_end(f)
            if k < 2:
                l1s.append(((x - w / 2, e[1], x + w / 2, e[1] + 1.2), e[2]))
                y, z = e[1] + 1.2, e[2]
            else:
                l1s.append(((x - w / 2, e[1], x + w / 2, e[1] + w), e[2]))
                y4, z = e[1] + w / 2, e[2]
                x4 = x - sx * (w / 2)   # inner edge of the landing; the flight leaves toward the centre
        f1s.append(flight(x4, y4, z, -sx, 0, w, 15, riser, 0.3))
        add_stair('S_GR1' + s, 'LOBBY', 'GL2', f1s, l1s, kind='grand')
        for f in f1s: add_hole_for_flight(f, LEVELS['L2'])
        add_headroom_holes(l1s, LEVELS['L2'])
        xA, xB = sx * 6.6, sx * 3.2
        a1 = flight(xA, YG, LEVELS['L2'], 0, -1, 3.2, 15, riser, 0.3); e = flight_end(a1)
        ml1 = ((xA - 1.6, e[1] - 1.2, xA + 1.6, e[1]), e[2])
        a2 = flight(xA, e[1] - 1.2, e[2], 0, -1, 3.2, 15, riser, 0.3); e = flight_end(a2)
        xs = sorted([xA - 1.6, xA + 1.6, xB - 1.6, xB + 1.6])
        tl = ((xs[0], e[1] - 3.2, xs[-1], e[1]), e[2])
        b1 = flight(xB, e[1], e[2], 0, 1, 3.2, 15, riser, 0.3); eb = flight_end(b1)
        ml2 = ((xB - 1.6, eb[1], xB + 1.6, eb[1] + 1.2), eb[2])
        b2 = flight(xB, eb[1] + 1.2, eb[2], 0, 1, 3.2, 15, riser, 0.3)
        add_stair('S_GR2' + s, 'GL2', 'GL3', [a1, a2, b1, b2], [ml1, tl, ml2], kind='grand')
        for f in (a1, a2, b1, b2): add_hole_for_flight(f, LEVELS['L3'])
        add_headroom_holes([ml1, tl, ml2], LEVELS['L3'])
    add_open('LOBBY', 'GL2', 'y', YG, -14, 14, [], check_z=False)  # logical only (stairs link); no wall changes
    EDGES.pop()  # (not a real link)
    OPENS.pop()
    # ring platforms in the atrium (L2, L3)
    for lv in ('L2', 'L3'):
        add_space('RW_' + lv, lv, (-14, 32, -10, 60), kind='platform', walls=False, ceil=False, zone='C')
        add_space('RE_' + lv, lv, (10, 32, 14, 60), kind='platform', walls=False, ceil=False, zone='C')
        add_space('RN_' + lv, lv, (-10, 56, 10, 60), kind='platform', walls=False, ceil=False, zone='C')
        # deep enough that the straight walk from the bridge centre to a side ring stays on a slab
        add_space('RS_' + lv, lv, (-10, 32, 10, 44), kind='platform', walls=False, ceil=False, zone='C')
        g = 'GL2' if lv == 'L2' else 'GL3'
        add_open(g, 'RW_' + lv, 'y', 32, -14, -10, [])
        add_open(g, 'RE_' + lv, 'y', 32, 10, 14, [])
        add_open(g, 'RS_' + lv, 'y', 32, -10, 10, [])
        add_open('RW_' + lv, 'RN_' + lv, 'x', -10, 56, 60, [])
        add_open('RE_' + lv, 'RN_' + lv, 'x', 10, 56, 60, [])
        add_open('RW_' + lv, 'RS_' + lv, 'x', -10, 32, 44, [])
        add_open('RE_' + lv, 'RS_' + lv, 'x', 10, 32, 44, [])
    # these OPENS entries list bands=[] -> no wall removal (platforms have no walls anyway)

    # ---------------- wings (W / E)
    for sx in (-1, 1):
        s = 'W' if sx == -1 else 'E'
        for lv in L3:
            R = lambda r: mirror_rect(r, sx, 1)
            cid = '%s_CORR_%s' % (s, lv)
            add_space(cid, lv, R((-66, -34, -62, 34)), kind='corridor', zone='wing' + s)
            ys = [-34, -17, 0, 17, 34]
            for k in range(4):
                y0, y1 = ys[k], ys[k + 1]
                yc = (y0 + y1) / 2
                rid = '%s_IN%d_%s' % (s, k, lv)
                add_space(rid, lv, R((-62, y0, -54, y1)), kind='gallery', zone='wing' + s)
                xin = mirror_rect((-62, 0, -62, 1), sx, 1)[0]
                room_link(cid, rid, 'x', xin, yc, 2.4, 3.2, lv)
            for k in (0, 3):
                y0, y1 = ys[k], ys[k + 1]; yc = (y0 + y1) / 2
                rid = '%s_OUT%d_%s' % (s, k, lv)
                add_space(rid, lv, R((-74, y0, -66, y1)), kind='gallery', zone='wing' + s)
                xo = mirror_rect((-66, 0, -66, 1), sx, 1)[0]
                room_link(cid, rid, 'x', xo, yc, 2.4, 3.2, lv)
            if True:
                hid = '%s_BUMP_%s' % (s, lv)
                add_space(hid, lv, R((-90, -17, -66, 17)), kind='hall', zone='wing' + s)
                xo = mirror_rect((-66, 0, -66, 1), sx, 1)[0]
                add_door(cid, hid, 'x', xo, 0.0, 3.2, 4.6, lv)
            else:
                for k in (1, 2):
                    y0, y1 = ys[k], ys[k + 1]; yc = (y0 + y1) / 2
                    rid = '%s_OUT%d_%s' % (s, k, lv)
                    add_space(rid, lv, R((-74, y0, -66, y1)), kind='gallery', zone='wing' + s)
                    xo = mirror_rect((-66, 0, -66, 1), sx, 1)[0]
                    add_door(cid, rid, 'x', xo, yc, 2.4, 3.2, lv)

    # ---------------- north wing (both halves)
    xsplit = [-54, -54 + 40 / 3.0, -54 + 80 / 3.0, -14]
    for sx in (-1, 1):
        s = 'W' if sx == -1 else 'E'
        for lv in L3:
            R = lambda r: mirror_rect(r, sx, 1)
            cid = 'N%s_CORR_%s' % (s, lv)
            add_space(cid, lv, R((-54, 38, -14, 42)), kind='corridor', zone='nwing' + s)
            for k in range(3):
                x0, x1 = xsplit[k], xsplit[k + 1]
                xc = (x0 + x1) / 2
                for row, (y0, y1, ycor) in (('S', (30, 38, 38)), ('N', (42, 50, 42))):
                    rid = 'N%s_%s%d_%s' % (s, row, k, lv)
                    add_space(rid, lv, R((x0, y0, x1, y1)), kind='gallery', zone='nwing' + s)
                    cx = mirror_pt(xc, 0, sx, 1)[0]
                    room_link(cid, rid, 'y', ycor, cx, 2.4, 3.2, lv)

    # ---------------- corner pavilions
    for (sx, sy), q in QN.items():
        R = lambda r: mirror_rect(r, sx, sy)
        P = lambda x, y: mirror_pt(x, y, sx, sy)
        for lv in L3:
            hid = 'PAV_%s_HALL_%s' % (q, lv)
            add_space(hid, lv, R((-70, 34, -54, 60)), kind='pavilion_hall', zone='pav' + q)
            lid = 'PAV_%s_LOB_%s' % (q, lv)
            add_space(lid, lv, R((-80, 34, -70, 42.8)), kind='core_lobby', zone='pav' + q, anchor=P(-72, 41.4))
            cab = 'PAV_%s_CAB_%s' % (q, lv)
            add_space(cab, lv, R((-80, 34, -74, 40)), kind='elevator', zone='pav' + q, h=10.0, ceil=False)
            sh = 'PAV_%s_SHAFT_%s' % (q, lv)
            # south wall at 42.8 (was 45): the 15-riser U needs the approach inside the shaft.
            # north edge is the shared start and end of the U (Y0). One tread past that (46.6) put the
            # shaft rail across the first riser, because the rail only opens within 5 cm of a flight end.
            arr = (-80, 42.8, -70, 46.30)
            add_space(sh, lv, R((-80, 42.8, -70, 60)), kind='stair', zone='pav' + q, ceil=False, floor=[R(arr)],
                      anchor=P(-75, 44.4))
            xw = P(-70, 0)[0]
            add_door(hid, lid, 'x', xw, P(0, 40)[1], 2.4, 4.2, lv)
            add_door(hid, sh, 'x', xw, P(0, 44.4)[1], 2.0, 4.2, lv)
            xc = P(0, 0)[0]
            ycab = P(0, 40)[1]
            add_door(lid, cab, 'y', ycab, P(-77, 0)[0], 1.6, 3.6, lv, kind='elevator_door')
        # wing corridor <-> pavilion hall (wall y = +-34), x = wing corridor center
        ywall = P(0, 34)[1]
        xcorr = P(-64, 0)[0]
        wing = ('W' if sx == -1 else 'E')
        for lv in L3:
            add_door('%s_CORR_%s' % (wing, lv), 'PAV_%s_HALL_%s' % (q, lv), 'y', ywall, xcorr, 3.2, 4.6, lv)
        # north wing corridor <-> pavilion hall (wall x = -+54)
        if sy == 1:
            xwall = P(-54, 0)[0]
            for lv in L3:
                add_door('N%s_CORR_%s' % (wing, lv), 'PAV_%s_HALL_%s' % (q, lv), 'x', xwall, 40, 3.2, 4.6, lv)
        # stairs between levels (switchback) L1->L2->L3->L4
        for k in range(3):
            lv, lv2 = ORDER[1 + k], ORDER[2 + k]
            zL = LEVELS[lv]
            # U stair, 3.0 m flights hugging the shaft side walls (5 cm gap). 10 m rise at 1/6 m = 4 x 15.
            # Turn landing north edge is y=59.50, half a metre inside the shaft wall at y=60.
            # The U leaves and returns on y=46.30, which is also the shaft slab's north edge.
            xA, xB, W3, Y0 = -78.05, -71.75, 3.0, 46.30
            RS = (LEVELS[lv2] - LEVELS[lv]) / 60
            fl, ld = [], []
            a1 = flight(xA, Y0, zL, 0, 1, W3, 15, RS, 0.3); e = flight_end(a1); fl.append(a1)
            ld.append(((xA - 1.5, e[1], xA + 1.5, e[1] + 1.2), e[2]))
            a2 = flight(xA, e[1] + 1.2, e[2], 0, 1, W3, 15, RS, 0.3); e = flight_end(a2); fl.append(a2)
            ld.append(((xA - 1.5, e[1], xB + 1.5, e[1] + 3.0), e[2]))
            b1 = flight(xB, e[1], e[2], 0, -1, W3, 15, RS, 0.3); e = flight_end(b1); fl.append(b1)
            ld.append(((xB - 1.5, e[1] - 1.2, xB + 1.5, e[1]), e[2]))
            b2 = flight(xB, e[1] - 1.2, e[2], 0, -1, W3, 15, RS, 0.3); fl.append(b2)
            fl = [mirror_flight(f, sx, sy) for f in fl]
            ld = [(R(r), z) for r, z in ld]
            add_stair('S_PAV_%s_%s' % (q, lv), 'PAV_%s_SHAFT_%s' % (q, lv), 'PAV_%s_SHAFT_%s' % (q, lv2), fl, ld)
        # elevator links
        for k in range(2):
            EDGES.append(dict(type='elevator', a='PAV_%s_CAB_%s' % (q, ORDER[1 + k]), b='PAV_%s_CAB_%s' % (q, ORDER[2 + k])))
        # L4 mech level (shaft top + mech hall)
        sh4 = 'PAV_%s_SHAFT_L4' % q
        add_space(sh4, 'L4', R((-78, 42.8, -70, 58)), kind='stair', zone='pav' + q, ceil=False, h=4.0,
                  floor=[R((-78, 42.8, -70, 46.30))], anchor=P(-74, 44.4))
        # h=4.0 (was 2.6) so the 3.4 m door has its own 0.6 m lintel, not only the mech wall
        mech = 'PAV_%s_MECH' % q
        add_space(mech, 'L4', R((-70, 40, -60, 56)), kind='mech', zone='pav' + q, ceil=False, h=5.0)
        add_door(sh4, mech, 'x', P(-70, 0)[0], P(0, 44.4)[1], 2.0, 3.4, 'L4')
        # L4 shaft spaces need the level-4 stair target; the L3->L4 stair created above targets SHAFT_L4 (OK)
    # ---------------- doors from north-wing corridors into the atrium / ring balconies
    for sx in (-1, 1):
        s = 'W' if sx == -1 else 'E'
        xwall = -14 if sx == -1 else 14
        add_door('N%s_CORR_L1' % s, 'ATRIUM', 'x', xwall, 40, 3.2, 5.0, 'L1')
        for lv in ('L2', 'L3'):
            add_door('N%s_CORR_%s' % (s, lv), 'R%s_%s' % (s, lv), 'x', xwall, 40, 3.2, 5.0, lv)
    if TOWER_OPEN: open_towers()
    return SPACES

def space_at_band(band):
    return [s for s in SPACES.values() if band in s['bands'] and s['walls']]

if __name__ == '__main__':
    build()
    print(len(SPACES), 'spaces', len(DOORS), 'doors', len(STAIRS), 'stairs', len(EDGES), 'edges')
    print(HOLES)
