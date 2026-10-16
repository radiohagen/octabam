"""Sparse SRAM claims retain every conflict without an all-pairs scan."""
import pathlib
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from remix import ledger


def oracle(windows):
    # The previous implementation, including declaration-order diagnostics.
    return [(earlier, later) for later, b in enumerate(windows)
            for earlier, a in enumerate(windows[:later])
            if a[0] < b[0] + b[1] and b[0] < a[0] + a[1]]


class SramClaims(unittest.TestCase):
    def test_boundaries_nested_duplicates_and_unsorted_windows(self):
        windows = [(8, 2), (0, 10), (2, 2), (4, 4), (0, 10), (10, 1),
                   (3, 0), (8, -2)]
        self.assertEqual(ledger._sram_overlaps(windows), oracle(windows))

    def test_seeded_selections_keep_all_conflicts_and_order(self):
        rng = random.Random(714)
        for _ in range(1000):
            windows = [(rng.randrange(-16, 128), rng.randrange(-2, 40))
                       for _ in range(rng.randrange(80))]
            self.assertEqual(ledger._sram_overlaps(windows), oracle(windows))

    def test_dense_overlaps_are_not_short_circuited(self):
        windows = [(0, 2)] * 128
        self.assertEqual(ledger._sram_overlaps(windows), oracle(windows))

    def test_sparse_midi_pool_and_one_conflict(self):
        windows = [(0x10000000 + i * 32, 2) for i in range(8192)]
        windows.append((windows[4096][0] + 1, 1))
        # Count work rather than timing a particular machine. The inserted
        # byte must still collide with its owner; adjacent empty gaps do not.
        with patch.object(ledger, '_overlap', wraps=ledger._overlap) as overlap:
            self.assertEqual(ledger._sram_overlaps(windows), [(4096, 8192)])
            self.assertLess(overlap.call_count, 8192)


if __name__ == '__main__':
    unittest.main()
