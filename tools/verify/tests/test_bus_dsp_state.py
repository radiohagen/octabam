"""The cache exception must reject corrupt scratch even if audio is silent."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import toolpath  # noqa: E402,F401
from verify_bus_dsp_state import STATE_WORDS, delay_cache_invariants  # noqa: E402


def row(block, count=256, **words):
    result = [block] + [0] * STATE_WORDS
    result[1+0x82] = 0x2e0000 | count
    result[1+0x26] = 0x4080  # A settled half-sample fraction is legitimate.
    result[1+0x6f] = 64
    result[1+0x7e] = 0x400000
    for offset, value in words.items():
        result[1+int(offset, 16)] = value
    return result


class DelayCacheInvariants(unittest.TestCase):
    def test_warming_rows_do_not_grant_an_exception(self):
        rows = [row(0, 1, **{"6e": 123}), row(1, 2, **{"6e": 456})]
        self.assertEqual(delay_cache_invariants(rows, 1), [None, None])

    def test_unsplit_last_warm_call_is_not_yet_live(self):
        rows = [row(0, 255), row(1, 256, **{"6e": 123}), row(2)]
        checks = delay_cache_invariants(rows, 1)
        self.assertEqual(checks[:2], [None, None])
        self.assertTrue(all(checks[2].values()))

    def test_split_crossing_warm_boundary_checks_the_same_block(self):
        rows = [row(0, 255), row(1)]
        checks = delay_cache_invariants(rows, 2)
        self.assertIsNone(checks[0])
        self.assertTrue(all(checks[1].values()))
        rows[1][1+0x6e] = 123
        self.assertFalse(delay_cache_invariants(rows, 2)[1][0x6e])

    def test_first_live_bad_mask_is_checked_even_if_baseline_had_that_word(self):
        # No comparison with baseline can exempt this predicate. Block one
        # stands for the first live block and is deliberately before 512.
        rows = [row(0, **{"6e": 0x654321}), row(1, **{"6e": 0x654321})]
        self.assertFalse(delay_cache_invariants(rows, 1)[1][0x6e])

    def test_zero_mask_checks_both_cache_words_and_no_other_state(self):
        good = delay_cache_invariants([row(0), row(1)], 1)[1]
        self.assertEqual(good, {0x6e: True, 0x6f: True, 0x7e: True})
        for offset in (0x6f, 0x7e):
            with self.subTest(offset=offset):
                bad = row(1)
                bad[1+offset] ^= 1
                self.assertFalse(delay_cache_invariants([row(0), bad], 1)[1][offset])

    def test_active_steps_require_exact_or_and_unchanged_caches(self):
        active = row(1, **{"36": 0xfffffe, "37": 1, "2f": 0x80,
                           "64": 0x400, "6e": 0xffffff, "26": 0x1100})
        self.assertTrue(all(delay_cache_invariants([row(0), active], 1)[1].values()))
        for offset in (0x6f, 0x7e):
            with self.subTest(offset=offset):
                bad = active.copy()
                bad[1+offset] ^= 1
                self.assertFalse(delay_cache_invariants([row(0), bad], 1)[1][offset])

    def test_signed_time_clamps_match_the_dsp_bounds(self):
        for q8, lag in ((0x800000, 8), (0x100, 8), (0x7fffff, 0x7ff8)):
            with self.subTest(q8=q8):
                current = row(1, **{"26": q8, "6f": lag, "7e": 0})
                self.assertTrue(all(delay_cache_invariants([row(0), current], 1)[1].values()))

    def test_invalid_call_count_is_rejected(self):
        with self.assertRaises(ValueError):
            delay_cache_invariants([], 0)


if __name__ == "__main__":
    unittest.main()
