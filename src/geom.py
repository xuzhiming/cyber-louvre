"""Tiny mesh accumulator (pure python/numpy). Groups -> materials -> verts/faces."""
import math, numpy as np

def _clip_poly(pts, axis, val, keep_greater):
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        da = (a[axis] - val) * (1 if keep_greater else -1)
        db = (b[axis] - val) * (1 if keep_greater else -1)
        if da >= 0: out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out

class Acc:
    def __init__(self):
        self.g = {}   # group -> mat -> [verts, faces]
        self.xclip = None   # (xmin, xmax) section slab
    def _b(self, group, mat):
        return self.g.setdefault(group, {}).setdefault(mat, [[], []])
    # ---------- low level
    def add_face(self, group, mat, pts):
        if self.xclip is not None:
            pts = [tuple(map(float, p)) for p in pts]
            pts = _clip_poly(pts, 0, self.xclip[0], True)
            if len(pts) >= 3: pts = _clip_poly(pts, 0, self.xclip[1], False)
            if len(pts) < 3: return
        v, f = self._b(group, mat)
        n = len(v)
        v.extend(pts)
        f.append(tuple(range(n, n + len(pts))))
    def add_faces_oriented(self, group, mat, faces, center):
        """faces: list of point lists; flip so normal points away from center."""
        c = np.array(center, float)
        for pts in faces:
            p = np.array(pts, float)
            nrm = np.cross(p[1] - p[0], p[2] - p[0])
            if len(p) > 3:  # robust normal (Newell)
                nrm = np.zeros(3)
                for i in range(len(p)):
                    a, b = p[i], p[(i + 1) % len(p)]
                    nrm += np.array([(a[1]-b[1])*(a[2]+b[2]), (a[2]-b[2])*(a[0]+b[0]), (a[0]-b[0])*(a[1]+b[1])])
            if np.dot(nrm, p.mean(0) - c) < 0:
                pts = pts[::-1]
            self.add_face(group, mat, [tuple(map(float, q)) for q in pts])
    # ---------- primitives
    def box(self, group, mat, x0, y0, z0, x1, y1, z1):
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        if z1 < z0: z0, z1 = z1, z0
        cutm = [None] * 6
        if self.xclip is not None:
            if x1 <= self.xclip[0] or x0 >= self.xclip[1]: return
            if x0 < self.xclip[0]: x0 = self.xclip[0]; cutm[0] = 'poche'
            if x1 > self.xclip[1]: x1 = self.xclip[1]; cutm[1] = 'poche'
        P = lambda x, y, z: (x, y, z)
        F = [
            [P(x0,y0,z0), P(x0,y0,z1), P(x0,y1,z1), P(x0,y1,z0)],
            [P(x1,y0,z0), P(x1,y1,z0), P(x1,y1,z1), P(x1,y0,z1)],
            [P(x0,y0,z0), P(x1,y0,z0), P(x1,y0,z1), P(x0,y0,z1)],
            [P(x0,y1,z0), P(x0,y1,z1), P(x1,y1,z1), P(x1,y1,z0)],
            [P(x0,y0,z0), P(x0,y1,z0), P(x1,y1,z0), P(x1,y0,z0)],
            [P(x0,y0,z1), P(x1,y0,z1), P(x1,y1,z1), P(x0,y1,z1)],
        ]
        for k, q in enumerate(F):
            v, f = self._b(group, cutm[k] or mat)
            n = len(v); v.extend(q); f.append((n, n+1, n+2, n+3))
    def rect(self, group, mat, r, z0, z1):
        self.box(group, mat, r[0], r[1], z0, r[2], r[3], z1)
    def hexa(self, group, mat, c):
        """c: 8 corners indexed (ix,iy,iz)-> c[ix+2*iy+4*iz]"""
        c = [tuple(map(float, p)) for p in c]
        idx = lambda ix, iy, iz: ix + 2*iy + 4*iz
        quads = [[(0,0,0),(0,0,1),(0,1,1),(0,1,0)], [(1,0,0),(1,1,0),(1,1,1),(1,0,1)],
                 [(0,0,0),(1,0,0),(1,0,1),(0,0,1)], [(0,1,0),(0,1,1),(1,1,1),(1,1,0)],
                 [(0,0,0),(0,1,0),(1,1,0),(1,0,0)], [(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
        ctr = np.mean(c, 0)
        faces = [[c[idx(*q)] for q in quad] for quad in quads]
        self.add_faces_oriented(group, mat, faces, ctr)
    def bar(self, group, mat, p0, p1, w, h, up=(0, 0, 1)):
        p0 = np.array(p0, float); p1 = np.array(p1, float)
        d = p1 - p0; L = np.linalg.norm(d)
        if L < 1e-6: return
        d /= L
        up = np.array(up, float)
        if abs(np.dot(d, up)) > 0.98: up = np.array([1.0, 0, 0])
        s = np.cross(d, up); s /= np.linalg.norm(s)
        u = np.cross(s, d)
        corners = []
        for iz in (0, 1):
            for iy in (0, 1):
                for ix in (0, 1):
                    base = p0 if ix == 0 else p1
                    corners.append(base + s * (iy - .5) * w + u * (iz - .5) * h)
        # reorder: our index uses ix as along-length
        self.hexa(group, mat, corners)
    def prism(self, group, mat, poly, plane, a0, a1, cap=True):
        """convex polygon extruded. plane 'xz' (extrude y), 'yz' (extrude x), 'xy' (extrude z)."""
        def m(p, a):
            if plane == 'xz': return (p[0], a, p[1])
            if plane == 'yz': return (a, p[0], p[1])
            return (p[0], p[1], a)
        n = len(poly)
        c0 = np.mean([m(p, (a0 + a1) / 2) for p in poly], 0)
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces.append([m(poly[i], a0), m(poly[j], a0), m(poly[j], a1), m(poly[i], a1)])
        if cap:
            faces.append([m(p, a0) for p in poly]); faces.append([m(p, a1) for p in poly])
        self.add_faces_oriented(group, mat, faces, c0)
    def flat(self, group, mat, pts, hint):
        p = np.array(pts, float)
        nrm = np.zeros(3)
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            nrm += np.array([(a[1]-b[1])*(a[2]+b[2]), (a[2]-b[2])*(a[0]+b[0]), (a[0]-b[0])*(a[1]+b[1])])
        if np.dot(nrm, hint) < 0: pts = pts[::-1]
        self.add_face(group, mat, [tuple(map(float, q)) for q in pts])
    def cyl(self, group, mat, cx, cy, z0, z1, r0, n=12, r1=None, caps=True):
        r1 = r0 if r1 is None else r1
        ring = lambda r, z: [(cx + r*math.cos(2*math.pi*k/n), cy + r*math.sin(2*math.pi*k/n), z) for k in range(n)]
        self.loft(group, mat, [ring(r0, z0), ring(r1, z1)], caps=caps, center=(cx, cy, (z0+z1)/2))
    def loft(self, group, mat, rings, caps=True, center=None, outward=True):
        n = len(rings[0])
        pts = np.array([p for r in rings for p in r], float)
        c = np.array(center) if center is not None else pts.mean(0)
        faces = []
        for a in range(len(rings) - 1):
            for i in range(n):
                j = (i + 1) % n
                faces.append([rings[a][i], rings[a][j], rings[a+1][j], rings[a+1][i]])
        if caps:
            faces.append(list(rings[0])); faces.append(list(rings[-1]))
        if outward:
            self.add_faces_oriented(group, mat, faces, c)
        else:
            for f in faces: self.add_face(group, mat, [tuple(map(float, q)) for q in f])
    def rect_ring(self, cx, cy, hx, hy, z):
        return [(cx-hx, cy-hy, z), (cx+hx, cy-hy, z), (cx+hx, cy+hy, z), (cx-hx, cy+hy, z)]
    # ---------- output
    def stats(self):
        t = 0
        for g in self.g.values():
            for v, f in g.values():
                for q in f: t += len(q) - 2
        return t
    def tri_by_group(self):
        return {gn: sum(len(q) - 2 for v, f in g.values() for q in f) for gn, g in self.g.items()}
    def all_faces_np(self, groups=None):
        """returns verts (N,3), polys list for BVH"""
        V, P = [], []
        for gn, g in self.g.items():
            if groups is not None and gn not in groups: continue
            for mat, (v, f) in g.items():
                o = len(V); V.extend(v)
                P.extend([tuple(i + o for i in q) for q in f])
        return V, P

def rect_minus(rect, holes, eps=1e-6):
    """rect (x0,y0,x1,y1) minus list of hole rects -> list of rects"""
    out = [tuple(rect)]
    for h in holes:
        nxt = []
        for r in out:
            ix0, iy0, ix1, iy1 = max(r[0], h[0]), max(r[1], h[1]), min(r[2], h[2]), min(r[3], h[3])
            if ix0 >= ix1 - eps or iy0 >= iy1 - eps:
                nxt.append(r); continue
            if iy0 > r[1] + eps: nxt.append((r[0], r[1], r[2], iy0))
            if iy1 < r[3] - eps: nxt.append((r[0], iy1, r[2], r[3]))
            if ix0 > r[0] + eps: nxt.append((r[0], iy0, ix0, iy1))
            if ix1 < r[2] - eps: nxt.append((ix1, iy0, r[2], iy1))
        out = nxt
    return out
