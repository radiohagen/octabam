"""Decode POST FADER's transient control tag, only in opted-in DSP builds.

Bit 23 represents the ORIGINAL send's participation; low 23 bits carry its
LEVEL-scaled value. Counts must use the former, ramps only the latter. This
preserves all other senders' normalization when a track is muted or faded.
The ColdFire halfword's low byte remains fractional precision, except for
BusDelay REV where TEMPO SYNC owns it. No persistent state layout changes.
"""


def _once(src: str, old: str, new: str) -> str:
    count = src.count(old)
    if count != 1:
        raise ValueError(f"POST FADER source anchor occurs {count} times, expected one: {old!r}")
    return src.replace(old, new, 1)


def transform(name: str, src: str) -> str:
    """Run before RETURNS and normal XBUS/address substitutions."""
    if name == "SEND":
        for load in ("        move    x:(r6),a                ; DEL level",
                     "        move    x:(r6+$1),a             ; REV level"):
            src = _once(src, load + "\n        and     #>$7f0000,a             ; the companion byte is not the knob",
                        load + "\n        and     #>$800000,a             ; POST FADER: original participation")
        for old, load in (("        move    x:(r6),y1                ; DEL level: the target", "x:(r6)"),
                          ("        move    x:(r6+$1),y1             ; REV level, ramped the same way", "x:(r6+$1)")):
            src = _once(src, old, f"""        move    {load},a
        and     #>$7fff00,a             ; POST FADER: scaled fraction, no tag
        move    a1,y1                   ; A1 avoids stale negative A2""")
        return src
    if name == "REVERB SERVER":
        src = _once(src, """        move    x:(r6+$1),a             ; REV (slot 1 since 26 Sep 2026, slot 0
        and     #>$7f0000,a             ; until then), the knob field: the
                                        ; host's own dry into the REV bus
        move    a1,y:>$981              ; the REV client flag (shared window)""", """        move    x:(r6+$1),a             ; POST FADER: original REV participation
        and     #>$800000,a
        move    a1,y:>$981              ; flag independent of LEVEL/mute
        move    x:(r6+$1),a
        and     #>$7fff00,a             ; scaled REV including fraction""")
        src = _once(src, """        move    x:(r6),a                ; DEL (slot 0), the knob field
        and     #>$7f0000,a
        move    a,y1""", """        move    x:(r6),a                ; POST FADER: scaled DEL
        and     #>$7fff00,a
        move    a1,y1                   ; remove stale negative A2
        move    y1,a""")
        # The firmware can send an unscaled initialization record before
        # pf_frame runs. DEL setup precedes the tank warmup, but the sample
        # loop that advances its ramp does not run while warming. Keep the
        # existing sentinel until processing starts, so the first real
        # sample seeds from its current scaled target, not the init record.
        # Once warm, this branch is never entered and running tails/ramp
        # smoothing are untouched.
        src = _once(src, """        bra     dry                     ; output stays dry until warm
warmdone:""", """        move    #>$ffffff,a            ; POST FADER: defer DEL seed until warm
        move    a,y:>$09f4
        bra     dry                     ; output stays dry until warm
warmdone:""")
        return _once(src, """        move    x:(r6),a                ; DEL
        and     #>$7f0000,a""", """        move    x:(r6),a                ; POST FADER: original DEL participation
        and     #>$800000,a""")
    if name == "DELAY SERVER":
        # The note shares REV's tagged word. Clean A2 before the shift:
        # cleaning afterwards cannot undo the sign bits shifted into A1.
        src = _once(src, """        move    x:(r6+$1),a
        and     #>$7f00,a               ; the note, bits 8-15
        asr     #$8,a,a""", """        move    x:(r6+$1),a
        and     #>$7f00,a               ; POST FADER: held note, no tag
        move    a1,x0
        move    x0,a                    ; clean A2 BEFORE shifting the note
        asr     #$8,a,a""")
        src = _once(src, """        move    x:(r6),a                ; AUX (slot 0): the host's own send
        and     #>$7f0000,a             ; knob field only""", """        move    x:(r6),a                ; POST FADER: original DEL participation
        and     #>$800000,a""")
        src = _once(src, """        move    x:(r6),a                ; SEND, slot 0
        and     #>$7f0000,a
        move    a,x:(r7+$2d)            ; SEND, this block
        move    a,y1""", """        move    x:(r6),a                ; POST FADER: scaled DEL with fraction
        and     #>$7fff00,a
        move    a1,y1                   ; remove stale negative A2
        move    y1,a
        move    a,x:(r7+$2d)            ; SEND, this block""")
        src = _once(src, """        move    x:(r6+$1),a             ; REV, slot 1
        and     #>$7f0000,a             ; knob field only
        move    a,x:(r7-$20)            ; REV, this block
        move    a,y1""", """        move    x:(r6+$1),a             ; POST FADER: REV; low byte is held note
        and     #>$7f0000,a
        move    a1,y1                   ; remove stale negative A2
        move    y1,a
        move    a,x:(r7-$20)            ; REV, this block""")
        return _once(src, "        move    x:(r7-$20),a            ; REV, this block\n        tst     a",
                     "        move    x:(r6+$1),a             ; POST FADER: original REV participation\n        and     #>$800000,a\n        tst     a")
    return src
