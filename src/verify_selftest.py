"""Negative control: build the walls WITHOUT door cut-outs and make sure the verifier notices."""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec, arch, exterior, verify
from geom import Acc
from mathutils import Vector
from mathutils.bvhtree import BVHTree
spec.build()
saved = list(spec.DOORS); spec.DOORS.clear()
acc = Acc(); arch.build_walls(acc); arch.build_slabs(acc); arch.build_stairs(acc); arch.build_rails(acc); exterior.pyramids(acc)
spec.DOORS.extend(saved)
V, P = acc.all_faces_np(groups=verify.BLOCK_GROUPS)
tris = [(q[0], q[i], q[i + 1]) for q in P for i in range(1, len(q) - 1)]
bvh = BVHTree.FromPolygons([Vector(v) for v in V], tris)
doors = verify.check_doors(bvh)
print('NEGATIVE CONTROL (walls without openings): doors reported cut =', sum(d['cut'] for d in doors), 'of', len(doors))
adj = verify.build_graph(); prev = verify.bfs(adj, 'PLAZA')
w = verify.walk_report(bvh, adj, prev, 'no openings')
print('walk paths ok', w['ok'], 'of', w['paths'])

# ---- negative control for the light-fixture check: put the OLD long ceiling strips back and expect violations
def _old_fixtures():
    import props, verify
    def old(sp, zc):
        x0, y0, x1, y1 = sp['rect']; lx, ly = x1 - x0, y1 - y0; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return [(x0 + 1.2, cy - 0.35, zc, x1 - 1.2, cy + 0.35, zc + 0.06)] if lx >= ly else [(cx - 0.35, y0 + 1.2, zc, cx + 0.35, y1 - 1.2, zc + 0.06)]
    props.ceiling_fixtures = old
    r = verify.check_fixtures()
    print('NEGATIVE CONTROL (old long B1 light strips): fixture violations =', r['violations'], '| e.g.', r['details'][:2])
_old_fixtures()


# ---- negative control for the stair-design rules: put the OLD lobby grand stair back (one 48-riser flight, 0.6 m from
# the entrance wall, no landings) and pull one pavilion stair leg 0.5 m off its wall; the audit must flag both.
def _old_stairs():
    import stair_rules
    import spec as sp
    bvh, acc = verify.build_bvh()
    ok_rows, ok_holes = stair_rules.audit(bvh, acc)
    print('STAIR RULES control (current design): violations =', sum(len(r['issues']) for r in ok_rows) + sum(len(h['unguarded']) for h in ok_holes))
    orig = sp.build
    def patched():
        r = orig()
        st = [s for s in sp.STAIRS if s['id'] == 'S_GR1W'][0]
        st['flights'] = [sp.flight(-11.75, 9.0, 0.0, 0, 1, 3.5, 48, 8.0 / 48, 0.3)]; st['landings'] = []
        pv = [s for s in sp.STAIRS if s['id'] == 'S_PAV_NW_L1'][0]
        for f in pv['flights']:
            if f['x'] < -75: f['x'] += 0.5
        return r
    sp.build = patched
    try:
        bvh2, acc2 = verify.build_bvh()
        rows, holes = stair_rules.audit(bvh2, acc2)
    finally:
        sp.build = orig
    bad = [(r['id'], r['issues']) for r in rows if r['issues']]
    print('NEGATIVE CONTROL (old lobby stair + pavilion stair leg 0.5 m off the wall): flagged', len(bad), 'stairs:')
    for b in bad: print('   ', b)
_old_stairs()

# ---- negative control for the stair-well / top-floor check: put the OLD closed mansard roof (solid cap at z=24 over each
# corner tower) back; the well check must flag the 4 corner-tower L3->L4 stairs (headroom ~0.17 m, arrival floor under a slab)
def _closed_roof():
    import exterior, spec as sp
    orig = exterior.roofs
    def old_roofs(acc, rng):
        orig(acc, rng)
        for m in sp.MASSES:
            if m['kind'] == 'pav':
                x0, y0, x1, y1 = m['rect']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                acc.add_faces_oriented('Roofs', 'roof_metal', [acc.rect_ring(cx, cy, 14.6, 14.6, 24.0)], (cx, cy, 33))
    exterior.roofs = old_roofs
    try:
        bvh, acc = verify.build_bvh()
        wells = verify.check_stair_wells(bvh)
    finally:
        exterior.roofs = orig
    bad = [(w['id'], w['min_head'], w['worst']) for w in wells if not w['ok']]
    print('NEGATIVE CONTROL (closed mansard cap over the corner-tower stairs): flagged', len(bad), 'of', len(wells), 'stairs:')
    for b in bad: print('   ', b)
_closed_roof()

# ---- negative control for the window check: windows painted on solid walls (no openings cut) must be flagged
def _closed_windows():
    import arch, exterior
    regs = [dict(axis=w['axis'], coord=w['coord'], a0=w['a0'], a1=w['a1'], z0=w['z0'], z1=w['z1'], out=w['out'], band=w['band']) for w in arch._windows()]
    orig = arch._windows
    arch._windows = lambda: []
    try:
        bvh, acc = verify.build_bvh()
        arch.WINDOW_CUTS[:] = regs
        r = verify.check_windows(bvh, acc)
    finally:
        arch._windows = orig
    print('NEGATIVE CONTROL (windows without wall openings): open_through', r['open_through'], 'of', r['cuts'], '| e.g.', r['open_fail'][:2])
_closed_windows()

# ---- negative control for the pane check: OLD roof windows (solid dormer blocks on an intact roof shell, solid gable
# tympanum behind the gable window) - every roof pane must be flagged
def _solid_dormers():
    import exterior
    exterior.DORMER_OPEN = False
    try:
        bvh, acc = verify.build_bvh()
        r = verify.check_panes(acc)
    finally:
        exterior.DORMER_OPEN = True
    roof = {k: v for k, v in r['by_kind'].items() if not k.startswith('facade')}
    print('NEGATIVE CONTROL (solid dormers / gable): panes ok', r['ok'], 'of', r['panes'], '| roof panes [total, ok]:', roof)
_solid_dormers()
