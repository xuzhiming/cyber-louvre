"""Plan cut (z = floor + 1.0 m) of the corner-tower areas: wall boxes from arch.build_walls of a given src dir -> json.
usage: plan_tower.py SRC_DIR OUT.json"""
import sys, os, json
sys.path.insert(0, os.path.abspath(sys.argv[1]))
import spec, arch
spec.build()
class Rec:
    def __init__(s): s.b = []
    def box(s, g, m, x0, y0, z0, x1, y1, z1): s.b.append((g, x0, y0, z0, x1, y1, z1))
r = Rec(); arch.build_walls(r)
out = {}
for lv, z in (('L1', 1.0), ('L2', 9.0), ('L3', 17.0)):
    out[lv] = [(g, x0, y0, x1, y1) for g, x0, y0, z0, x1, y1, z1 in r.b if z0 <= z <= z1]
out['spaces'] = {k: dict(rect=v['rect'], level=v['level'], kind=v['kind']) for k, v in spec.SPACES.items() if v['level'] in ('L1',)}
out['stairs'] = [[flight_step for flight_step in [spec.flight_step_rect(f, i)[0] for i in range(1, f['n'] + 1)]] for st in spec.STAIRS if st['id'].startswith('S_PAV') and st['id'].endswith('L1') for f in st['flights']]
out['removed'] = [dict(o) for o in getattr(spec, 'TOWER_OPENED', []) if o['band'] == 'L1']
json.dump(out, open(sys.argv[2], 'w'))
print(len(out['L1']), 'wall boxes at L1')
