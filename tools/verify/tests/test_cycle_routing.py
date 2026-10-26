"""A routing copy is extra work; a stereo word loop runs twice per frame."""
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import toolpath  # noqa: E402,F401
from build import cycle_count as cc  # noqa: E402


@unittest.skipUnless(cc.ASM.is_file(), "DSP assembler is required")
class RoutingCosts(unittest.TestCase):
    def price(self, source):
        with patch.object(cc, "prep", return_value=source):
            result = cc.measure("routing_fixture")
            self.assertTrue(cc.verify("routing_fixture", result))
            return result

    def test_interleaved_word_loop_costs_twice_per_frame(self):
        source = """proc:
        do #<$20,>wordend ; CYCLES_FRAME_LOOP
        nop
        nop
wordend:
        rts
"""
        self.assertEqual(self.price(source)["cycles"], 4)

    def test_auxiliary_copy_is_added_to_each_mode(self):
        source = """proc:
        do n7,>copyend ; CYCLES_AUX_LOOP
        nop
copyend:
        do x0,>modeone ; CYCLES_SAMPLE_LOOP
        nop
        nop
modeone:
        do n7,>modetwo
        nop
        nop
        nop
modetwo:
        rts
"""
        result = self.price(source)
        self.assertEqual(result["cycles"], 4)
        self.assertEqual([row[2] for row in result["modes"]], [3, 4])

    def test_unannotated_fixed_loop_is_not_a_sample_loop(self):
        self.assertIsNone(cc.sample_loop("        do #<$20,>initend"))

    def test_hook_is_paid_even_when_a_dearer_insert_fills_slots(self):
        rows = [{"name": "insert", "cycles": 100},
                {"name": "returns", "cycles": 17, "fixed_hook": True}]
        mods = [dict(stem=name, key=name, server=False, fx1_only=False)
                for name in ("insert", "returns")]
        total, picks = cc.bank_worst(rows, mods)
        self.assertEqual(total, 417)
        self.assertEqual(dict(picks), {"insert": 4, "returns": 1})


if __name__ == "__main__":
    unittest.main()
