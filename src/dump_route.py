import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify
bvh, acc = verify.build_bvh()
adj = verify.build_graph(skip=lambda e: e['type'] == 'door' and e['door'].get('kind') == 'main_door')
prev = verify.bfs(adj, 'PLAZA')
def route(t):
    chain = []; c = t
    while prev[c] is not None:
        u, e = prev[c]; chain.append((u, c, e)); c = u
    pts = []; names = ['PLAZA']
    for u, v, e in chain[::-1]:
        P = verify.edge_path(bvh, u, v, e)
        names.append(v)
        if P is None: continue
        pts += [[round(float(x), 3) for x in p] for p in P]
    # drop duplicates
    out = []
    for p in pts:
        if not out or max(abs(a - b) for a, b in zip(p, out[-1])) > 0.05: out.append(p)
    return names, out
n, p = route('GL2')
print(n, len(p))
json.dump({'GL2': {'spaces': n, 'pts': p}}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_route.json'), 'w'))
