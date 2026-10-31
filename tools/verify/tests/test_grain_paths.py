"""Both exact GRAIN density paths follow the same two/four-grain lever."""
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
from build import cycle_count as cc  # noqa: E402
from remix import geom, grains  # noqa: E402
from verify_delay import mode_count  # noqa: E402


class GrainPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "modules/busdelay/delay_server.asm").read_text()

    def test_both_paths_roll_and_keep_the_same_public_modes(self):
        self.assertEqual(grains.census(self.source), [])
        two = grains.roll(self.source, 2)
        self.assertEqual(two.count("        do      #2,"), 4)
        self.assertNotIn("        do      #4,", two)
        self.assertEqual(two.count("        asl     #$1,b,b"), 4)
        self.assertEqual(two.count("grain-to-grain offset G/4 -> G/2"), 1)
        self.assertEqual(mode_count(self.source), 3)
        self.assertEqual(mode_count(two), 3)

    def test_marked_source_requires_every_path_marker(self):
        for marker in ("; GRAINCNT\n", "; GRAINMK\n"):
            with self.subTest(marker=marker):
                damaged = self.source.replace(marker, "", 2)
                self.assertIn((marker, 2, 4), grains.census(damaged))
                with self.assertRaises(ValueError):
                    grains.roll(damaged, 2)
        self.assertTrue(grains.census(self.source.replace(grains.DENSITY_PATHS, "")))

    def test_historical_single_pair_has_an_explicit_distinct_census(self):
        legacy = ("; GRAINCNT\n        do      #4,>end\n" * 2
                  + "; GRAINOFF\n" + "; GRAINMK\n" * 2)
        self.assertEqual(grains.census(legacy), [])
        self.assertEqual(grains.roll(legacy, 2).count("        do      #2,"), 2)
        self.assertTrue(grains.census(grains.DENSITY_PATHS + legacy))

    @unittest.skipUnless(cc.ASM.is_file(), "DSP assembler is required")
    def test_pricer_treats_readers_as_alternatives_for_both_grain_counts(self):
        costs = []
        for count in (4, 2):
            source = geom.select(grains.roll(self.source, count), False)
            with patch.object(cc, "prep", return_value=source):
                priced = cc.measure("grain_paths_fixture")
                self.assertTrue(cc.verify("grain_paths_fixture", priced))
            paths = [row[2] for row in priced["modes"]]
            self.assertEqual(len(paths), 3)  # dense GRAIN, sparse GRAIN, REVERSE
            self.assertEqual(priced["cycles"], max(paths))
            costs.append(priced["cycles"])
        self.assertLess(costs[1], costs[0])


if __name__ == "__main__":
    unittest.main()
