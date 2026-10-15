"""Sparse retained pools must remain precise without quadratic idle work."""
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from remix.ledger import _sram_overlaps


class SramOverlapTests(unittest.TestCase):
    def test_matches_pairwise_oracle_and_diagnostic_order(self):
        rng = random.Random(431)
        cases = [[(0, 8), (8, 2), (2, 3), (0, 8), (4, 0)],
                 [(10, -2), (0, 20), (5, 4)]]
        cases += [[(rng.randrange(100), rng.randrange(-1, 25))
                   for _ in range(60)] for _ in range(100)]
        cases += [[(rng.randrange(100), rng.randrange(1, 25))
                   for _ in range(60)] for _ in range(100)]
        for ranges in cases:
            expected = [(i, j) for i, (a, n) in enumerate(ranges)
                        for j, (b, m) in enumerate(ranges[:i])
                        if a < b + m and b < a + n]
            self.assertEqual(_sram_overlaps(ranges), expected)

    def test_precise_pool_and_crossing_claim(self):
        pool = [(0x1001614e + p*0x8ed8 + 0x4900 + t*0x8b0 + s*32 + 30, 2)
                for p in range(16) for t in range(8) for s in range(64)]
        self.assertEqual(_sram_overlaps(pool), [])
        at = pool[123][0]
        self.assertEqual(_sram_overlaps(pool + [(at - 1, 4)]), [(8192, 123)])


if __name__ == '__main__':
    unittest.main()
