import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify
bvh, acc = verify.build_bvh()
adj = verify.build_graph(skip=lambda e: e['type'] == 'elevator')
out = {}
for q in ('NW', 'NE', 'SW', 'SE'):
    src = 'PAV_%s_SHAFT_L1' % q; dst = 'PAV_%s_SHAFT_L4' % q
    prev = verify.bfs(adj, src); chain = []; c = dst
    while prev[c] is not None:
        u, e = prev[c]; chain.append((u, c, e)); c = u
    pts = []
    for u, v, e in chain[::-1]:
        P = verify.edge_path(bvh, u, v, e)
        pts += [[round(float(x), 3) for x in p] for p in P]
    o = []
    for p in pts:
        if not o or max(abs(a - b) for a, b in zip(p, o[-1])) > 0.05: o.append(p)
    out[q] = {'spaces': [src] + [v for _, v, _ in chain[::-1]], 'pts': o}
    print(q, out[q]['spaces'], len(o), o[0], o[-1])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_route_towers.json'), 'w'))
