"""Circulation diagram: plan per floor with walk graph, doors, stairs and example routes."""
import os, sys, math, collections
import numpy as np
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import spec
from spec import *
import verify

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
COL = dict(room='#2a3a66', gallery='#35467a', corridor='#4a6aa8', hall='#3e4f8f', pavilion_hall='#3e4f8f', core_lobby='#4a5a9a', elevator='#8a5aa8',
           stair='#a8567a', lobby='#6a4aa0', atrium='#5a3a90', platform='#2aa8a8', concourse='#4a5a70', pyramid='#2a9ab0', outdoor='#161c30', mech='#6a5a3a')

def level_of_z(z):
    best = min(ORDER, key=lambda l: abs(LEVELS[l] - z)); return best

def main():
    bvh, acc = verify.build_bvh()
    adj = verify.build_graph(); prev = verify.bfs(adj, 'PYR_MAIN')
    adj2 = verify.build_graph(skip=lambda e: e['type'] == 'door' and e['door']['kind'] == 'main_door')
    prev = verify.bfs(adj2, 'PYR_MAIN')
    targets = [('PAV_NE_MECH', '#ffd23f'), ('PAV_SW_HALL_L3', '#3fff9a'), ('E_BUMP_L2', '#ff6a3f'), ('PAV_SE_CAB_L3', '#ff3fd0')]
    routes = {}
    for t, c in targets:
        chain = []; cur = t
        while prev[cur] is not None:
            u, e = prev[cur]; chain.append((u, cur, e)); cur = u
        chain = chain[::-1]
        pts = []
        for (u, v, e) in chain:
            P = verify.edge_path(bvh, u, v, e)
            if P is None:   # elevator hop: draw marker between cabs
                continue
            pts.extend([(p[0], p[1], p[2]) for p in P])
        routes[t] = (pts, c, len(chain))
    fig, axes = plt.subplots(2, 3, figsize=(24, 12.8), facecolor='#0a0e1c')
    levels = ['B1', 'L1', 'L2', 'L3', 'L4']
    for ax, lv in zip(axes.flat, levels):
        ax.set_facecolor('#0a0e1c'); ax.set_aspect('equal'); ax.set_xlim(-96, 96); ax.set_ylim(-76, 66)
        ax.set_title({'B1': 'B1  z -6.0  (concourse under the courtyard)', 'L1': '1F  z +0.0', 'L2': '2F  z +8.0', 'L3': '3F  z +16.0', 'L4': 'Roof / mech  z +24.0'}[lv],
                     color='w', fontsize=15)
        ax.tick_params(colors='#667', labelsize=8)
        z = LEVELS[lv]
        for sp in SPACES.values():
            on = (sp['level'] == lv) or (lv in sp['bands'] and len(sp['bands']) > 1)
            if not on: continue
            r = sp['rect']
            tall = (sp['level'] != lv)
            fc = COL.get(sp['kind'], '#334')
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], facecolor=fc, edgecolor='#cfd6ff' if sp['walls'] else '#5fe0e8',
                                   lw=0.8, alpha=0.55 if tall else 0.85, hatch='//' if tall else None, linestyle='-' if sp['walls'] else '--'))
        for d in DOORS:
            if d['band'] != lv: continue
            (cx, cy, z0), n = verify.door_world(d)
            if d['axis'] == 'x': ax.plot([cx, cx], [cy - d['width'] / 2, cy + d['width'] / 2], color='#ffb347', lw=3.2, solid_capstyle='butt')
            else: ax.plot([cx - d['width'] / 2, cx + d['width'] / 2], [cy, cy], color='#ffb347', lw=3.2, solid_capstyle='butt')
        for st in STAIRS:
            for f in st['flights']:
                e = flight_end(f)
                za, zb = f['z0'], e[2]
                if (min(za, zb) - 0.01 <= z <= max(za, zb) + 0.01) or abs(za - z) < 0.01 or abs(zb - z) < 0.01 or (lv == level_of_z(min(za, zb)) ) or (lv == level_of_z(max(za, zb))):
                    ax.add_patch(FancyArrowPatch((f['x'], f['y']), (e[0], e[1]), arrowstyle='-|>', mutation_scale=14, color='#ff4f6a', lw=2.6))
        for e in EDGES:
            if e['type'] == 'elevator':
                a, b = SPACES[e['a']], SPACES[e['b']]
                if a['level'] == lv or b['level'] == lv:
                    ax.plot(*a['anchor'], marker='^', color='#d28aff', ms=9)
        # routes (each point belongs to the floor whose band contains its z)
        def lvl(zz):
            return 'B1' if zz < -3 else 'L1' if zz < 4 else 'L2' if zz < 12 else 'L3' if zz < 20 else 'L4'
        for t, (pts, col, n) in routes.items():
            seg = []
            for p in pts:
                if lvl(p[2]) == lv: seg.append((p[0], p[1]))
                else:
                    if len(seg) > 1: ax.plot(*zip(*seg), color=col, lw=2.6, alpha=0.95)
                    seg = []
            if len(seg) > 1: ax.plot(*zip(*seg), color=col, lw=2.6, alpha=0.95)
        # labels
        for sid in ('LOBBY', 'ATRIUM', 'PLAZA', 'PYR_MAIN', 'B1_HALL', 'B1_SPINE'):
            sp = SPACES[sid]
            if lv in sp['bands'] or sp['level'] == lv:
                ax.text(sp['anchor'][0], sp['anchor'][1], sid.replace('_', ' ').title(), color='w', fontsize=9, ha='center')
        if lv in ('L1', 'L2', 'L3'):
            for q, (px, py) in {'NW': (-67, 47), 'NE': (67, 47), 'SW': (-67, -47), 'SE': (67, -47)}.items():
                ax.text(px, py + 10, 'PAV ' + q, color='#cfd6ff', fontsize=8, ha='center')
    ax = axes.flat[5]; ax.axis('off'); ax.set_facecolor('#0a0e1c')
    rep = __import__('json').load(open(os.path.join(OUT, 'connectivity_report.json')))
    lines = ['CIRCULATION  (walk graph)', '',
             'spaces: %d   doors: %d   stairs: %d   elevators links: %d' % (rep['spaces'], rep['doors'], rep['stairs'], 8),
             'all reachable from plaza: %s' % ('YES' if not rep['unreached_from_plaza'] else 'NO'),
             'reachable from pyramid entrance only: %s' % ('YES' if not rep['unreached_pyramid_only'] else 'NO'),
             'reachable by stairs only (no elevators): %s' % ('YES' if not rep['unreached_no_elevator'] else 'NO'),
             'door openings cut through walls: %d / %d' % (rep['doors_cut_ok'], rep['doors']),
             'stairs OK: %d / %d  (riser max %.3f m, tread min %.2f m, min headroom %.2f m)' % (rep['stairs_ok'], rep['stairs'], rep['max_riser_m'], rep['min_tread_m'], rep['min_headroom_m']),
             '', 'legend:  amber bar = door opening    red arrow = stair flight (low->high)',
             '         purple triangle = elevator    dashed outline = open platform / glass', '',
             'example routes from the main (pyramid) entrance:']
    for t, (pts, c, n) in routes.items(): lines.append('   %s  -> %s  (%d hops)' % ('■', t, n))
    ax.text(0.0, 1.0, '\n'.join(lines), color='w', fontsize=11.5, va='top', family='monospace', transform=ax.transAxes)
    y = 0.22
    for t, (pts, c, n) in routes.items():
        ax.plot([0.02, 0.08], [y, y], color=c, lw=4, transform=ax.transAxes); ax.text(0.1, y, t, color='w', fontsize=12, va='center', transform=ax.transAxes); y -= 0.05
    plt.tight_layout()
    os.makedirs(os.path.join(OUT, 'renders'), exist_ok=True)
    fig.savefig(os.path.join(OUT, 'renders/circulation_diagram.png'), dpi=80, facecolor=fig.get_facecolor())
    print('saved')
if __name__ == '__main__':
    main()
