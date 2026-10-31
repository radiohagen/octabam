"""Fault injection for complete Y-data comparison; no program-memory claim."""
import array
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import toolpath  # noqa: E402,F401
from verify_bus_fastpaths import compare_y_data


class YDataTests(unittest.TestCase):
    def setUp(self):
        self.before = array.array("I", [0] * 0x40000)
        self.after = array.array("I", self.before)

    def compare(self):
        return compare_y_data(self.before.tobytes(), self.after.tobytes())["final_y_data_identical"]

    def test_all_words_equal(self):
        self.assertTrue(self.compare())

    def test_private_buffer_difference_is_rejected(self):
        self.after[0x4000] = 1
        self.assertFalse(self.compare())

    def test_shared_bus_difference_is_rejected(self):
        self.after[0x36011] = 1
        self.assertFalse(self.compare())

    def test_shared_y_difference_at_program_address_is_rejected(self):
        # P:$35811 contains different program words between these builds.
        # P is separate in dsp_host; its address grants no Y-data exclusion.
        self.after[0x35811] = 0x69c
        self.assertFalse(self.compare())

    def test_both_shared_boundaries_are_checked(self):
        for address in (0x30000, 0x3ffff):
            with self.subTest(address=hex(address)):
                self.after[address] = 1
                self.assertFalse(self.compare())
                self.after[address] = 0

    def test_matching_empty_captures_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete Y"):
            compare_y_data(b"", b"")

    def test_one_truncated_capture_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete Y"):
            compare_y_data(self.before.tobytes(), self.after.tobytes()[:-4])


if __name__ == "__main__":
    unittest.main()
