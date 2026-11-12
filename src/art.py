"""Artwork display slots: fixed-size frames on every side wall / partition of the opened gallery bays.
Slots are exported to web/slots.json; the web viewer hangs bidder.art works into them (media loaded lazily online)."""
import os, json
import spec
from spec import BAND_Z, SPACES, ORDER
import arch

SLOT_W, SLOT_H = 2.0, 1.5        # outer frame size (m)
FRAME = 0.08                     # frame border width
DEPTH = 0.05                     # frame depth off the wall face
Z_CENTER = 1.6                   # centre height above the storey floor
PER_FACE = 2                     # slots per wall face (face net length 7.6 m)
SLOTS = []
DROPPED = []                     # faces dropped because their wall was removed (room, band, axis, coord)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def faces():
    """display faces of every opened gallery bay: (room, band, axis_of_wall, wall_coord, face_coord, normal, u0, u1)"""
    res = []
    zone_order = {'wingW': 0, 'nwingW': 1, 'nwingE': 2, 'wingE': 3}
    # walking order (t29u: hang from 1F upwards): storey by storey, and on each storey one loop through the galleries -
    # west wing south -> north, north wing west half west -> east, east half west -> east, east wing north -> south
    def walk_key(o):
        sp = SPACES[o['room']]; r = sp['rect']; cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2; z = sp['zone']
        along = {'wingW': cy, 'nwingW': cx, 'nwingE': cx, 'wingE': -cy}.get(z, 0.0)
        return (ORDER.index(o['band']), zone_order.get(z, 9), round(along, 2), o['room'])
    opened = sorted(spec.OPENED, key=walk_key)
    for o in opened:
        r = SPACES[o['room']]['rect']; ti = arch.T_INT / 2; te = arch.T_EXT / 2
        if o['axis'] == 'x':                 # door wall vertical at x=coord, room extends along x, side walls are y = r1 / r3
            far = r[0] if o['n'][0] < 0 else r[2]
            ua, ub = sorted((o['coord'], far - o['n'][0] * te))
            res.append((o['room'], o['band'], 'y', r[1], r[1] + ti, (0, 1), ua, ub))
            res.append((o['room'], o['band'], 'y', r[3], r[3] - ti, (0, -1), ua, ub))
        else:
            far = r[1] if o['n'][1] < 0 else r[3]
            ua, ub = sorted((o['coord'], far - o['n'][1] * te))
            res.append((o['room'], o['band'], 'x', r[0], r[0] + ti, (1, 0), ua, ub))
            res.append((o['room'], o['band'], 'x', r[2], r[2] - ti, (-1, 0), ua, ub))
    # walls removed later (t27u corner-tower opening: wall to the tower / between the tower's neighbour rooms) carry no art
    def removed(f):
        _, band, wax, wc, _, _, ua, ub = f
        return any(o['axis'] == wax and abs(o['coord'] - wc) < 1e-3 and band in o['bands'] and min(o['a1'], ub) - max(o['a0'], ua) > 0.5
                   for o in spec.OPENS)
    DROPPED[:] = [(f[0], f[1], f[2], f[3]) for f in res if removed(f)]
    return [f for f in res if not removed(f)]

def build_slots():
    SLOTS.clear()
    for k, (room, band, wax, wc, fc, n, u0, u1) in enumerate(faces()):
        L = u1 - u0; z = BAND_Z[band][0] + Z_CENTER
        for j in range(PER_FACE):
            u = u0 + L * (j + 0.5) / PER_FACE
            if wax == 'y': p = (u, fc + n[1] * DEPTH, z)
            else: p = (fc + n[0] * DEPTH, u, z)
            SLOTS.append(dict(id='S%03d' % len(SLOTS), room=room, band=band, face=k, wall_axis=wax, wall_coord=wc, face_coord=fc,
                              u=u, pos=[round(v, 4) for v in p], normal=[n[0], n[1], 0], size=[SLOT_W, SLOT_H],
                              inner=[round(SLOT_W - 2 * FRAME, 3), round(SLOT_H - 2 * FRAME, 3)]))
    return SLOTS

def build_frames(acc, write=True):
    build_slots()
    for s in SLOTS:
        x, y, z = s['pos']; n = s['normal']; hw, hh = SLOT_W / 2, SLOT_H / 2
        if s['wall_axis'] == 'y':
            y0 = s['face_coord']; y1 = y0 + n[1] * DEPTH
            B = lambda a0, a1, z0, z1, d0, d1, m: acc.box('ArtFrames', m, a0, y0 + n[1] * d0, z0, a1, y0 + n[1] * d1, z1)
            u = x
        else:
            x0 = s['face_coord']
            B = lambda a0, a1, z0, z1, d0, d1, m: acc.box('ArtFrames', m, x0 + n[0] * d0, a0, z0, x0 + n[0] * d1, a1, z1)
            u = y
        B(u - hw, u + hw, z - hh, z - hh + FRAME, 0.0, DEPTH, 'frame_dark')
        B(u - hw, u + hw, z + hh - FRAME, z + hh, 0.0, DEPTH, 'frame_dark')
        B(u - hw, u - hw + FRAME, z - hh + FRAME, z + hh - FRAME, 0.0, DEPTH, 'frame_dark')
        B(u + hw - FRAME, u + hw, z - hh + FRAME, z + hh - FRAME, 0.0, DEPTH, 'frame_dark')
        B(u - hw + FRAME, u + hw - FRAME, z - hh + FRAME, z + hh - FRAME, 0.0, DEPTH - 0.02, 'art_canvas')   # recessed backing
    if write:
        json.dump(dict(slot_size=[SLOT_W, SLOT_H], inner=[SLOT_W - 2 * FRAME, SLOT_H - 2 * FRAME], depth=DEPTH, z_center=Z_CENTER,
                       per_face=PER_FACE, coords='world: x east, y north, z up (three.js = x, z, -y); pos = frame front centre',
                       count=len(SLOTS), slots=SLOTS), open(os.path.join(OUT, 'web', 'slots.json'), 'w'), indent=0)
    return SLOTS
