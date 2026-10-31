"""BusDelay's GRAIN reader: four grains per line, or two.

One copy of the substitution, imported by both the builder and the pricer,
so the image and `make cycles` agree. Three edits, at markers in the engine
source:

  ; GRAINCNT   both rolled readers in each density path count 2 instead of 4
  ; GRAINOFF   the grain-to-grain phase offset doubles, G/4 -> G/2, so two
              grains still tile the cycle
  ; GRAINMK    the makeup doubles: four triangle windows at quarter offsets
              sum to exactly 2, two at half offsets sum to exactly 1

The doubling is `asl #$1`, which keeps the extension byte consistent with
A1 (a logical shift would leave A2 stale and the next store would saturate).
"""

MARKERS = (("; GRAINCNT\n", 2), ("; GRAINOFF\n", 1), ("; GRAINMK\n", 2))
DENSITY_PATHS = "; GRAIN_DENSITY_PATHS\n"


def census(src):
    """[(marker, found, expected)] for every marker whose count is wrong."""
    # Historical reference sources have one reader pair. The explicit marker
    # declares two mutually exclusive pairs; do not accept a missing pair in
    # that source merely because two markers would fit the old layout.
    paths = src.count(DENSITY_PATHS)
    counts = [(m, n * 2 if paths and m != "; GRAINOFF\n" else n)
              for m, n in MARKERS]
    if paths:
        counts.append((DENSITY_PATHS, 1))
    return [(m, src.count(m), n) for m, n in counts if src.count(m) != n]


def roll(src, grains):
    """The delay source with its GRAIN reader rolled to `grains` per line."""
    if grains == 4:
        return src
    bad = census(src)
    if bad:
        raise ValueError("; ".join(f"{m.strip()}: {f} markers, expected {n}"
                                   for m, f, n in bad))
    src = src.replace("; GRAINCNT\n        do      #4,", "        do      #2,")
    # G/4 arrives in `a` at the marker and the engine stores it on the next
    # line (14 Sep 2026: the r7 rebase moved every slot's spelling, so the
    # lever names no slot at all -- it doubles what is in the accumulator).
    src = src.replace("; GRAINOFF\n", """        asl     #$1,a,a                 ; grain-to-grain offset G/4 -> G/2
""", 1)
    return src.replace("; GRAINMK\n", """        asl     #$1,b,b                 ; two windows sum to 1, not 2
""")
