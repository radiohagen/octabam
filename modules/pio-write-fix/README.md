# PIO WRITE FIX

This selects Yves Rosius's existing `stems_ata_first` fix independently of
STEM REC. Its instructions are unchanged; the build checks their SHA-256
against an independently assembled extraction of `modules/stems/stems.s`.
It adds no recording feature, UI, task, state or persistence format.

## Problem and behavior

Stock sends the first sector of a PIO card write before updating the shared
next-sector pointer and remaining count. If another task preempts that update,
the card interrupt can send the first sector twice or wait forever for another
sector. A project save can therefore retain the right file length and still
have an invalid checksum. The fix advances both fields before sending data,
when the card cannot yet request the second sector.

The hook at `0x40014cfe` rejoins stock at `0x40014d58`, using the same `d0`,
`d1`, `a0` scratch registers. It affects all PIO writes. It never executes on
the separate WRITE DMA path. See [the original investigation](https://github.com/radiohagen/octabam/blob/codex/integrate/midi/docs/firmware/STEM_REC.md)
section 11.7 for the instruction trace and section 11.8 for the DMA distinction.

STEM REC already owns this hook, so selecting both is rejected. A future shared
extraction can make both consumers require one owner; this standalone module
avoids changing the recording implementation in a focused package repair.

## Verification boundary

`tools/verify/verify_pio_write.py` executes the installed hook with distinct
sector data, checks the fields at the last data word, simulates the immediate
card handler, and checks register preservation. The original stock code is a
negative control. The complete application must additionally pass its project
save, reload, retention and selected-remix gates on the same frozen image.

The emulator advertises a PIO-only card. This is no evidence of a failure on a
particular hardware card, of WRITE DMA behavior, or of a fix for the recurring
power-on logo hang. No hardware qualification is claimed here.
