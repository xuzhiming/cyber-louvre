"""Plan view of the 1F lobby stairs with clearances annotated.  usage: plan_view.py SRC_DIR OUT.png LABEL"""
import sys, os, json
src = os.path.abspath(sys.argv[1]); out = sys.argv[2]; label = sys.argv[3]
sys.path.insert(0, src)
import spec
from spec import *
spec.build()
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
fig, ax = plt.subplots(figsize=(8.2, 8.6), dpi=140)
XW, YS = 13.6, 8.4                    # inner faces of the lobby side walls / entrance wall
ax.add_patch(Rectangle((-14, 8), 28, 24, fc='#f4f1ea', ec='none', zorder=0))
for (x0, y0, x1, y1) in ((-14.8, 7.6, -13.6, 32.5), (13.6, 7.6, 14.8, 32.5)):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='#555', ec='none', zorder=3))
ax.add_patch(Rectangle((-14.8, 7.6), 29.6, 0.8, fc='#555', ec='none', zorder=3))
ax.add_patch(Rectangle((-3, 7.55), 6, 0.9, fc='#9fd8ff', ec='#2a6fa0', lw=1, zorder=4))
ax.text(0, 7.0, 'main entrance door  (6.0 m)', ha='center', va='top', fontsize=8, color='#2a6fa0')
# gallery bridges GL2 / GL3
for st in STAIRS:
    if st['id'].startswith('S_LOBBY'): col = '#bbbbbb'
    elif st['id'].startswith('S_GR1'): col = '#4a90d9'
    elif st['id'].startswith('S_GR2'): col = '#e08a2e'
    else: continue
    for f in st['flights']:
        for i in range(1, f['n'] + 1):
            r, zt = flight_step_rect(f, i)
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec='white', lw=0.25, zorder=2, alpha=0.9))
        ex = flight_end(f)
        ax.annotate('', xy=(ex[0], ex[1]), xytext=(f['x'], f['y']), arrowprops=dict(arrowstyle='->', color='k', lw=0.8), zorder=6)
    for r, z in st['landings']:
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec='k', lw=0.6, zorder=2, alpha=0.55, hatch='//'))
gl = SPACES['GL2']['rect']
ax.add_patch(Rectangle((gl[0], gl[1]), gl[2] - gl[0], gl[3] - gl[1], fc='none', ec='#8a4fff', lw=1.2, ls='--', zorder=5))
ax.text(0, gl[1] + 0.35, 'L2 / L3 gallery bridge edge', ha='center', fontsize=7, color='#8a4fff')
for z, hs in HOLES.items():
    for h in hs:
        ax.add_patch(Rectangle((h[0], h[1]), h[2] - h[0], h[3] - h[1], fc='none', ec='#d03030', lw=1.0, ls=':', zorder=5))
def dim(x0, y0, x1, y1, txt, col='#d03030', off=(0, 0), fs=8):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='<->', mutation_scale=7, color=col, lw=1.1, zorder=7))
    ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], txt, ha='center', va='center', fontsize=fs, color=col, zorder=8,
            bbox=dict(fc='white', ec='none', alpha=0.85, pad=0.8))
gr = [s for s in STAIRS if s['id'] == 'S_GR1W'][0]; f1 = gr['flights'][0]
xo = f1['x'] - f1['w'] / 2
dim(-XW, 17, xo, 17, '%.2f m' % (xo + XW), off=(0, 0.9))
dim(f1['x'] - 0.0, YS, f1['x'], f1['y'], '%.2f m' % (f1['y'] - YS), off=(1.6, 0), col='#d03030')
gl_ = sorted(set(round(f['y'], 2) for f in gr['flights']))
ee = flight_end(gr['flights'][-1])
dim(f1['x'] + 0.4, ee[1], f1['x'] + 0.4, gl[3], '%.1f m' % (gl[3] - ee[1]), col='#2a8a3a', off=(1.6, 0))
nf = len(gr['flights']); mr = max(f['n'] for f in gr['flights'])
ax.text(-15.6, 33.3, '%s\nL1->L2 flight: %d risers in %d flight(s), %d landing(s), width %.1f m\nedge-to-wall %.2f m | approach zone %.2f m' %
        (label, sum(f['n'] for f in gr['flights']), nf, len(gr['landings']), f1['w'], xo + XW, f1['y'] - YS),
        fontsize=8.5, va='bottom', ha='left')
ax.set_xlim(-16, 16); ax.set_ylim(6, 36); ax.set_aspect('equal'); ax.grid(alpha=0.2)
ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')
ax.text(15.8, 6.3, 'blue: L1->L2 grand stair   orange: L2->L3   grey: B1->L1   red dotted: slab opening   hatched: landings',
        fontsize=6.5, ha='right', color='#333')
fig.tight_layout(); fig.savefig(out); print('saved', out)
