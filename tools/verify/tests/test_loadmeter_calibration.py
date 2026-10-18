import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from verify_loadmeter import BURNS, TOL, calibration_deltas


class CalibrationTests(unittest.TestCase):
    def busy(self, gain=.5, setup=80):
        return {n: tuple(base + (setup + gain*n if n else 0) for base in (10000, 12000)) for n in BURNS}

    def passes(self, busy):
        return [abs(rise-want) <= TOL*want for _, _, _, rise, want in calibration_deltas(busy)]

    def test_equal_setup_cancels_without_expanding_tolerance(self):
        self.assertEqual(TOL, .05)
        self.assertEqual(self.passes(self.busy(setup=500)), [True]*4)

    def test_two_nonzero_differences_per_core(self):
        rows = list(calibration_deltas(self.busy()))
        self.assertEqual([(c, low, high) for c, low, high, _, _ in rows],
                         [(c, low, high) for c in (0, 1) for low, high in zip(BURNS[1:], BURNS[2:])])
        self.assertTrue(all(want == 960 for *_, want in rows))

    def test_dead_counter_is_rejected(self):
        self.assertEqual(self.passes(self.busy(gain=0)), [False]*4)

    def test_wrong_clock_ratio_is_rejected(self):
        self.assertEqual(self.passes(self.busy(gain=1)), [False]*4)

    def test_out_of_tolerance_gain_is_rejected(self):
        self.assertEqual(self.passes(self.busy(gain=.4)), [False]*4)

    def test_unburned_layout_is_not_a_calibration_baseline(self):
        before = self.busy()
        after = dict(before)
        after[0] = (0, 1000000)
        self.assertEqual(list(calibration_deltas(before)), list(calibration_deltas(after)))

    def test_three_positive_variants_required(self):
        with self.assertRaises(ValueError):
            list(calibration_deltas(self.busy(), (0, 1000, 3000)))


if __name__ == '__main__':
    unittest.main()
