"""Datum locks for the approved storey and door change. Pure Python, no Blender.

Riser stays 1/6 m. Pyramid glass doors stay. Every other real door is 1 m taller.
The L4 shaft wall must be tall enough for its own lintel.
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec
from spec import flight_end

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
