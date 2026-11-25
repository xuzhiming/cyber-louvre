"""Datum locks for the approved storey and door change. Pure Python, no Blender.

Riser stays 1/6 m. Pyramid glass doors stay. Every other real door is 1 m taller.
The L4 shaft wall must be tall enough for its own lintel.
The minimap and the HUD share one floor cut, taken from the plate heights.
"""
import json, os, re, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from spec import flight_end

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
STALE_FLOOR = ("y < -3 ? 'B1'", "zz < -3")

RISER = 1.0 / 6.0


class FloorHeightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.build()

    def test_levels_and_dome(self):
        self.assertEqual(spec.LEVELS, {'B1': -8.0, 'L1': 0.0, 'L2': 10.0, 'L3': 20.0, 'L4': 30.0})
        self.assertEqual(spec.BAND_Z['B1'], (-8.0, 0.0))
        self.assertEqual(spec.BAND_Z['L1'], (0.0, 10.0))
        self.assertEqual(spec.BAND_Z['L2'], (10.0, 20.0))
        self.assertEqual(spec.BAND_Z['L3'], (20.0, 30.0))
        self.assertEqual(spec.BAND_Z['L4'], (30.0, 40.0))
        self.assertEqual(spec.DOME['z0'], 40.0)
        self.assertEqual(spec.DOME['h'], 13.0)

    def test_outer_footprint_and_wall_tops(self):
        tops = {}
        for m in spec.MASSES:
            tops.setdefault(m['kind'], set()).add(m['h'])
            x0, y0, x1, y1 = m['rect']
            self.assertGreaterEqual(x0, -90.01)
            self.assertLessEqual(x1, 90.01)
            self.assertGreaterEqual(y0, -70.01)
            self.assertLessEqual(y1, 60.01)
        self.assertEqual(tops['pav'], {30})
        self.assertEqual(tops['wing'], {30})
        self.assertEqual(tops['bump'], {30})
        self.assertEqual(tops['nwing'], {30})
        self.assertEqual(tops['center'], {40})
        self.assertEqual(tops['drum'], {40})

    def test_room_heights(self):
        g = spec.SPACES['W_IN0_L1']
        self.assertEqual((g['z0'], g['z1']), (0.0, 10.0))
        b = spec.SPACES['B1_HALL']
        self.assertEqual((b['z0'], b['z1']), (-8.0, 0.0))
        self.assertEqual(spec.SPACES['LOBBY']['z1'], 40.0)
        self.assertEqual(spec.SPACES['ATRIUM']['z1'], 40.0)
        cab = spec.SPACES['PAV_NW_CAB_L1']
        self.assertEqual(cab['z1'] - cab['z0'], 10.0)
        mech = spec.SPACES['PAV_NW_MECH']
        self.assertEqual(mech['z1'] - mech['z0'], 5.0)

    def test_door_heights(self):
        glass = [d for d in spec.DOORS if d['glass']]
        self.assertEqual(sorted(d['height'] for d in glass), [2.8, 2.8, 4.5])
        main = [d for d in spec.DOORS if d['kind'] == 'main_door']
        self.assertEqual([(d['width'], d['height']) for d in main], [(6.0, 6.0)])
        for d in spec.DOORS:
            if d['glass']:
                continue
            if d['kind'] == 'elevator_door':
                self.assertEqual(d['height'], 3.6)
            elif d['kind'] == 'main_door':
                self.assertEqual(d['height'], 6.0)
            elif d['band'] == 'L4':
                self.assertEqual((d['width'], d['height']), (2.0, 3.4))
            elif abs(d['width'] - 3.2) < 1e-6 and abs(d['height'] - 4.0) < 1e-9:
                self.fail('north-wing door was not raised')
            elif abs(d['width'] - 3.2) < 1e-6:
                self.assertIn(d['height'], (4.6, 5.0))
            elif abs(d['width'] - 2.0) < 1e-6:
                self.assertEqual(d['height'], 4.2)

    def test_l4_shaft_lintel(self):
        for d in spec.DOORS:
            if d['band'] != 'L4':
                continue
            shaft = spec.SPACES[d['a'] if 'SHAFT' in d['a'] else d['b']]
            self.assertGreaterEqual(shaft['z1'] - shaft['z0'], d['height'] + 0.5)
            mech = spec.SPACES[d['b'] if 'MECH' in d['b'] else d['a']]
            self.assertGreaterEqual(mech['z1'] - mech['z0'], d['height'] + 0.5)

    def test_stairs_keep_original_riser(self):
        self.assertEqual(len(spec.STAIRS), 20)
        for st in spec.STAIRS:
            rise = st['end'][2] - st['start'][2]
            dz = spec.SPACES[st['b']]['z0'] - spec.SPACES[st['a']]['z0']
            self.assertAlmostEqual(rise, dz, places=6, msg=st['id'])
            ns = [f['n'] for f in st['flights']]
            self.assertLessEqual(max(ns), 18, st['id'])
            self.assertGreaterEqual(sum(ns), 48, st['id'])
            for f in st['flights']:
                self.assertAlmostEqual(abs(f['riser']), RISER, places=6, msg=st['id'])
                self.assertAlmostEqual(f['tread'], 0.30, places=6, msg=st['id'])
                self.assertGreaterEqual(f['w'], 1.8)
                two = 2 * abs(f['riser']) + f['tread']
                self.assertGreaterEqual(two, 0.60 - 1e-6)
                self.assertLessEqual(two, 0.64 + 1e-6)
            # landings meet the written minimums
            for i, (r, z) in enumerate(st['landings']):
                fa, fb = st['flights'][i], st['flights'][i + 1]
                turn = (fa['dx'], fa['dy']) != (fb['dx'], fb['dy'])
                depth = (r[3] - r[1]) if abs(fa['dy']) > 0.5 else (r[2] - r[0])
                need = fa['w'] if turn else 1.2
                self.assertGreaterEqual(depth + 1e-6, need, st['id'])
            # stay inside the outer footprint, with a small tolerance for a landing nose
            for f in st['flights']:
                e = flight_end(f)
                for x, y in ((f['x'], f['y']), (e[0], e[1])):
                    self.assertGreaterEqual(x, -90.5, st['id'])
                    self.assertLessEqual(x, 90.5, st['id'])
                    self.assertGreaterEqual(y, -70.5, st['id'])
                    self.assertLessEqual(y, 60.2, st['id'])

    def test_known_layouts(self):
        by = {st['id']: st for st in spec.STAIRS}
        self.assertEqual([f['n'] for f in by['S_PM']['flights']], [16, 16, 16])
        self.assertEqual([f['n'] for f in by['S_LOBBY']['flights']], [16, 16, 16])
        self.assertEqual([f['n'] for f in by['S_PSL']['flights']], [12, 12, 12, 12])
        self.assertEqual([f['n'] for f in by['S_GR1E']['flights']], [15, 15, 15, 15])
        self.assertEqual([f['n'] for f in by['S_GR2E']['flights']], [15, 15, 15, 15])
        self.assertEqual([f['n'] for f in by['S_PAV_NW_L1']['flights']], [15, 15, 15, 15])
        # grand run reaches the side gallery, not the atrium void
        end = by['S_GR1E']['end']
        self.assertGreater(end[1], 25.0)
        self.assertLess(end[1], 32.0)
        self.assertGreater(abs(end[0]), 4.0)
        self.assertLess(abs(end[0]), 12.0)
        # pavilion U stays inside the exterior wall
        pav = by['S_PAV_NW_L1']
        ys = []
        for f in pav['flights']:
            ys += [f['y'], flight_end(f)[1]]
        for r, _z in pav['landings']:
            ys += [r[1], r[3]]
        self.assertLess(max(ys), 59.7)
        self.assertGreater(min(f['y'] for f in pav['flights']), 42.8)

    def test_pavilion_slab_edge_meets_flights_and_rail_opens(self):
        """each tower's railed slab edge is the real flight start/end, and that flight is not walled off"""
        import arch
        from geom import Acc
        acc = Acc()
        arch.build_arch(acc)
        rails = acc.g.get('Rails', {}).get('rail_glass')
        self.assertIsNotNone(rails)
        V, F = rails

        def spans_at(y, z):
            raw = []
            for face in F:
                pts = [V[i] for i in face]
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
                # rail glass sits 3 cm off the slab edge, so accept a face whose y is that close
                if min(ys) - 0.08 <= y <= max(ys) + 0.08 and min(zs) <= z + 0.6 <= max(zs):
                    raw.append((min(xs), max(xs)))
            raw.sort()
            merged = []
            for a, b in raw:
                if merged and a <= merged[-1][1] + 0.02:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))
            return merged

        def covered(spans, x):
            return any(a - 1e-6 <= x <= b + 1e-6 for a, b in spans)

        for q in ('NW', 'NE', 'SW', 'SE'):
            for lv in ('L1', 'L2', 'L3', 'L4'):
                sp = spec.SPACES['PAV_%s_SHAFT_%s' % (q, lv)]
                x0, y0, x1, y1 = sp['rect']
                z = sp['z0']
                ends = []
                for st in spec.STAIRS:
                    if not st['id'].startswith('S_PAV_%s_' % q):
                        continue
                    for f in st['flights']:
                        e = flight_end(f)
                        for py, pz in ((f['y'], f['z0']), (e[1], e[2])):
                            if abs(pz - z) < 0.05:
                                ends.append((st['id'], f, py))
                self.assertTrue(ends, '%s %s has no flight on its floor' % (q, lv))
                railed = []
                for fr in sp['floor']:
                    for coord in (fr[1], fr[3]):
                        if abs(coord - y0) < 0.01 or abs(coord - y1) < 0.01:
                            continue
                        railed.append(coord)
                self.assertTrue(railed, '%s %s slab has no guarded edge' % (q, lv))
                for coord in railed:
                    for sid, f, py in ends:
                        self.assertLess(abs(py - coord), 0.05, '%s end y=%.3f vs slab edge %.3f' % (sid, py, coord))
                    spans = spans_at(coord, z)
                    for sid, f, py in ends:
                        for x in (f['x'] - f['w'] / 2 + 0.05, f['x'], f['x'] + f['w'] / 2 - 0.05):
                            self.assertFalse(covered(spans, x), '%s rail still crosses the flight at x=%.2f' % (sid, x))
                    # the well beside the flights stays guarded (not the sliver the rail builder drops under 0.2 m)
                    centers = sorted(set(round(f['x'], 4) for _, f, _ in ends))
                    fx0 = min(fr[0] for fr in sp['floor']); fx1 = max(fr[2] for fr in sp['floor'])
                    if len(centers) >= 2:
                        probe = (centers[0] + centers[1]) / 2
                    else:
                        f0 = ends[0][1]
                        probe = f0['x'] - f0['w'] / 2 - 1.0 if (f0['x'] - fx0) > (fx1 - f0['x']) else f0['x'] + f0['w'] / 2 + 1.0
                    self.assertTrue(fx0 < probe < fx1, '%s %s probe %.2f left the slab' % (q, lv, probe))
                    self.assertFalse(any(abs(probe - f['x']) <= f['w'] / 2 for _, f, _ in ends))
                    self.assertTrue(covered(spans, probe), '%s %s well is unguarded at x=%.2f' % (q, lv, probe))


class FloorNavTest(unittest.TestCase):
    def test_map_and_hud_share_plate_midpoints(self):
        pages = [os.path.join(ROOT, 'src', 'web_template.html'), os.path.join(ROOT, 'web', 'preview.html')]
        for path in pages:
            with open(path, encoding='utf-8') as fh:
                html = fh.read()
            for stale in STALE_FLOOR:
                self.assertFalse(stale in html, '%s still classifies floors with %s' % (os.path.basename(path), stale))
            m = re.search(r'function floorKeyFrom\(y, plates\) \{[\s\S]*?\n\}', html)
            self.assertIsNotNone(m, path)
            self.assertIn('return FLOOR_LABEL[floorKey(y)]', html)
            self.assertIn('const mmLevel = floorKey', html)
            self.assertIn('MM.plan.levels[k].z', html)
            js = m.group(0) + """
const plates = [{k:'B1',z:-8},{k:'L1',z:0},{k:'L2',z:10},{k:'L3',z:20},{k:'L4',z:30}];
const ys = [-8, -4, 0, 5, 10, 15, 20, 20.05, 25, 30];
const out = {};
for (const y of ys) out[String(y)] = floorKeyFrom(y, plates);
process.stdout.write(JSON.stringify(out));
"""
            got = json.loads(subprocess.check_output(['node', '-e', js], text=True))
            self.assertEqual(got, {
                '-8': 'B1', '-4': 'L1', '0': 'L1', '5': 'L2', '10': 'L2',
                '15': 'L3', '20': 'L3', '20.05': 'L3', '25': 'L4', '30': 'L4',
            }, path)
            # 3F works sit at z=21.6. On the L3 plan they fall in the map's slot window; on L4 they do not.
            self.assertIn('p[2] < zb - 0.5 || p[2] >= zb + 7.5', html)
            with open(os.path.join(ROOT, 'web', 'slots.json'), encoding='utf-8') as fh:
                slots = json.load(fh)['slots']
            art = [s for s in slots if s['band'] == 'L3']
            self.assertTrue(art)
            zb = spec.LEVELS['L3']
            shown = [s for s in art if zb - 0.5 <= s['pos'][2] < zb + 7.5]
            self.assertEqual(len(shown), len(art))
            self.assertTrue(all(abs(s['pos'][2] - (zb + 1.6)) < 1e-6 for s in shown))
            zb4 = spec.LEVELS['L4']
            self.assertTrue(all(s['pos'][2] < zb4 - 0.5 for s in shown))
        for dirpath, _, files in os.walk(os.path.join(ROOT, 'src')):
            for name in files:
                if name == 'test_floor_height.py' or not name.endswith(('.py', '.html')):
                    continue
                with open(os.path.join(dirpath, name), encoding='utf-8') as fh:
                    text = fh.read()
                for stale in STALE_FLOOR:
                    self.assertNotIn(stale, text, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
