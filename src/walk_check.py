import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify
from mathutils import Vector
d = json.load(open('../renders/walk/'+(sys.argv[1] if len(sys.argv)>1 else 'walk_test.json')+''))
bvh, acc = verify.build_bvh()
T = d['traj']; bad = 0; n = 0; minclr = 9
for a, b in zip(T[:-1], T[1:]):
    for h in (0.5, 1.0, 1.6):
        o = Vector((a[0], a[1], a[2] + h)); v = Vector((b[0], b[1], b[2] + h)) - o
        L = v.length
        if L < 1e-4: continue
        n += 1
        r = bvh.ray_cast(o, v.normalized(), L)
        if r[0] is not None: bad += 1; print('CROSS', a, b, h)
# clearance: min distance from sampled positions to nearest geometry (horizontal 8 dirs at 1.0 m)
import math
for p in T[::5]:
    for k in range(8):
        dv = Vector((math.cos(k*math.pi/4), math.sin(k*math.pi/4), 0))
        r = bvh.ray_cast(Vector((p[0], p[1], p[2] + 1.0)), dv, 2.0)
        if r[0] is not None: minclr = min(minclr, r[3])
res = f'samples {len(T)}, segment tests {n}, wall crossings {bad}, min horizontal clearance {minclr:.2f} m (capsule radius 0.35)'
print(res); open('../renders/walk/passthrough_'+(sys.argv[1] if len(sys.argv)>1 else 'walk_test.json').replace('.json','')+'.txt', 'w').write(res + '\n')
