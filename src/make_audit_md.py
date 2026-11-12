import json, os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
b = {r['id']: r for r in json.load(open(R + '/stair_audit_before.json'))['rows']}
a = {r['id']: r for r in json.load(open(R + '/stair_audit_after.json'))['rows']}
def gap(r):
    g = [x for x in r['gaps_flight0'] if x < 50]
    return '-' if not g else ('%.2f' % min(g))
def cell(r):
    ld = ','.join('%s %.1f' % (t[0][0], t[1]) for t in r['landings']) or 'none'
    return 'w %.1f; %d flt, max %d risers; tread %.2f, 2R+T %.3f; side-gap(min) %s; zones in/out %.1f/%.1f m (need %.1f); landings: %s; head %.2f' % (
        r['w'], r['flights'], r['max_risers'], r['tread'], r['2R+T'], gap(r), r['zone_start'], r['zone_end'], r['zone_req'], ld, r['headroom'])
groups = [('S_PM (main pyramid -> B1)', ['S_PM']), ('S_PSL / S_PSR (small pyramids -> B1)', ['S_PSL', 'S_PSR']),
          ('S_LOBBY (B1 spine -> lobby)', ['S_LOBBY']), ('S_GR1W / S_GR1E (grand stair L1->L2)', ['S_GR1W', 'S_GR1E']),
          ('S_GR2W / S_GR2E (grand stair L2->L3)', ['S_GR2W', 'S_GR2E']),
          ('S_PAV_{NW,NE,SW,SE}_{L1,L2,L3} (12 pavilion core stairs)', [k for k in a if k.startswith('S_PAV')])]
out = ['# Stair audit before / after', '', 'Rules: side gap to wall <=0.12 m (hugging, handrail on the wall side) or >=1.2 m; approach / exit zone >= max(width,1.8) m (grand >= max(width,3.0)); <=18 risers per flight; turn landing depth >= width, straight landing >= 1.2 m; riser 0.15-0.17, tread 0.30-0.32, 2R+T 0.60-0.64; headroom >= 2.4 m; handrails both sides; slab openings guarded; no door overlap.', '']
for title, ids in groups:
    r0, r1 = b[ids[0]], a[ids[0]]
    out += ['## ' + title, '- BEFORE: ' + cell(r0), '  - issues: ' + ('; '.join(r0['issues']) or 'none'),
            '- AFTER:  ' + cell(r1), '  - issues: ' + ('; '.join(r1['issues']) or 'none'), '']
tot0 = sum(len(r['issues']) for r in b.values()); tot1 = sum(len(r['issues']) for r in a.values())
bad0 = sum(1 for r in b.values() if r['issues']); bad1 = sum(1 for r in a.values() if r['issues'])
out += ['**Stairs with at least one violation: %d of %d before -> %d of %d after.**' % (bad0, len(b), bad1, len(a))]
open(R + '/stair_audit.md', 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
