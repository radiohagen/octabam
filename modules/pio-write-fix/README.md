# PIO Write Fix

Applies Yves Rosius's first-sector card-write ordering fix without adding
STEM REC or recording controls. It advances the next-sector pointer and
remaining count before sending the first sector, preventing the card handler
from observing stale write state.

Applies to PIO writes, not WRITE DMA. STEM REC owns the same hook, so the two
cannot be selected together. No project-file format changes are involved.

[Developer notes and verification](DEVELOPMENT.md).
