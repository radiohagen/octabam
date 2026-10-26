"""Select RETURNS routing without moving any byte of remixes lacking it.

Called only when RETURNS is selected, before the normal XBUS/YBase source
substitutions. Exact anchors refuse drift. The algorithms and read-back pad
stay in the engines; these inserts redirect their already-computed wet output.
Ported from sambanks/octabam PR542 with current memory allocation and ordinary
branches, so no historical assembler patch is required.
"""


def _once(src: str, anchor: str, replacement: str) -> str:
    count = src.count(anchor)
    if count != 1:
        raise ValueError(f"RETURNS source anchor occurs {count} times, expected one: {anchor!r}")
    return src.replace(anchor, replacement, 1)

RV_LATCH = r'''; ---- RETURNS (PR #542 return protocol): this block's print mode --------
; RETURNS on T8's FX2 writes the magic word to y:$e20 every block it runs;
; this call reads it on the block's first call, keeps it for the block in
; y:$e24 and clears it, so RETURNS gone for one block is normal print again.
; One writer (RETURNS), one clearer (here), both on core 0.
        tst     a                       ; a = this call's frame offset
        bne     rt_latched             ; not the block's first call
        move    y:>$e20,a
        move    a,y:>$e24               ; the mode: magic = returns
        clr     a
        move    a,y:>$e20
rt_latched:
'''

RV_PREFILL = r'''; ---- RETURNS: the print goes through the buffer y:$e00.. -----------------
; n4 = this call's range of the buffer, y:$e00 + 2 x the frame offset (the
; offset, not r0: the block's base is X:0 on the unit and X:$80 in dsp_host,
; AGENTS.md). Normal print: the range is prefilled with this call's dry and
; copied back to the block after the loop, so the block ends as dry + wet
; exactly as before. Returns: the range is prefilled with zero, the block
; keeps its dry, and the buffer ends as the wet alone for the mixdown hook.
; (29 Sep 2026: a return buffer in private X:$3e00 instead, beside the
; cross-core delay return, crackled and stopped the DSP on the unit --
; FAILURE_MODES.md; this Y form ran clean there as BSRET3 and RIGT3.)
; r4 (m4 = $fff) addresses the buffer: y:$e00..$e1f never crosses a 4096
; boundary, so the modulo never wraps it. r0 is left on the call's first
; sample.
        move    x:(r7+$5d),a            ; this call's frame offset
        asl     a                       ; frames -> words
        add     #>$e00,a
        move    a,n4
        move    a,r4
        move    y:>$e24,a
        cmp     #>$5a5a5a,a             ; Z = returns mode: one compare, the
        move    #0,x0                   ; Tcc below read it (moves and the do
        move    r0,x1                   ; r0 parked (the loop writes x1 first)
        do      n7,>rt_pfd ; CYCLES_AUX_LOOP
                                        ; leave the condition codes alone)
        move    x:(r0)+,a               ; dry L ...
        teq     x0,a                    ; ... or zero in returns mode
        move    a,y:(r4)+
        move    x:(r0)+,a               ; dry R ...
        teq     x0,a
        move    a,y:(r4)+
rt_pfd:
        move    x1,r0                   ; back on the call's first sample

'''

RV_END = r'''; ---- RETURNS: the normal print copies the buffer back into the block; the
; returns print leaves the block its dry and marks the buffer fresh for the
; mixdown hook (y:$e22, cleared by the hook: one writer, one reader).
        move    y:>$e24,a
        cmp     #>$5a5a5a,a
        beq     rt_fresh
        move    n4,r4                   ; r0 and n4 stepped 2 x n7 words in the
        move    r0,x1                   ; loop: copy back from the end down, R
        do      n7,>rt_cbd ; CYCLES_AUX_LOOP
                                        ; then L of each pair (the stock forms:
        move    y:-(r4),a               ; y:-(r5),a and a1,x:-(r1)), dry + wet
        move    a1,x:-(r0)              ; into the block as before
        move    y:-(r4),a
        move    a1,x:-(r0)
rt_cbd:
        move    x1,r0                   ; r0 leaves where it always has: past
                                        ; the call's last sample
        bra     noloop
rt_fresh:
        move    a,y:>$e22               ; FRESH (a holds the magic)
'''

DL_LATCH = r'''; ---- RETURNS (PR #542 return protocol, stage B) --------------------------
; RETURNS on T8's FX2 (core 0) stamps the shared word Y:$30208 every block
; it runs. The block's first call reads and clears it, the reverb's DELAY
; LIVE pattern (stampgr: 3 blocks of grace in raw $62, masked: r7 slots
; start as garbage), and keeps the result for the whole block in raw $65:
; nonzero = returns. Every call parks its PRINT TARGET in raw $66, carried
; through the sample loop in n7 (the count goes to the `do` through x0; n7
; is read by nothing else here, and is restored after the loop): normal, the
; block itself, so the print is in place exactly as before; returns, this
; call's range of the wet buffers, Y:$30100 + 2 x (write offset + frame
; offset), zeroed first, so the print leaves the wet alone there and T1
; keeps its dry. 8 buffers x 16 x (L, R), written at the write rotation like
; the CHAIN, read by core 0's mixdown hook three buffers back (through X:
; the window aliases X and Y).
        move    x:(r7+$1e),a            ; this call's frame offset
        tst     a
        bne     rtd_latched             ; not the block's first call
        move    x:(r7+$19),b            ; the grace (raw $62)
        and     #>$3,b                  ; boot garbage masked ...
        move    b1,x0
        move    x0,b                    ; ... and B2 clean
        move    #>$1,x0
        sub     x0,b
        move    #0,x0
        tmi     x0,b                    ; floored at 0
        move    #>$30208,a
        move    a,r5                    ; ALIVE_D
        move    #>$3,x1                 ; (spaces the r5 write)
        move    y:(r5),a                ; the stamp
        move    x0,y:(r5)               ; clear-on-read (x0 is 0)
        tst     a
        tne     x1,b                    ; stamped: 3 blocks of grace
        move    b,x:(r7+$19)
        move    b,x:(r7+$1c)            ; the mode (raw $65): grace left = returns
rtd_latched:
        move    r0,a                    ; normal: the block, in place
        move    x:(r7+$1c),b            ; the block's mode
        tst     b
        beq     rtd_ptr
        move    x:(r7-$29),a            ; returns: write offset (0..112)
        move    x:(r7+$1e),x0           ; + this call's frame offset
        add     x0,a
        asl     a                       ; stereo: 2 words a frame
        move    #>$30100,x0
        add     x0,a
        move    a,r4                    ; the range, zeroed (m4 is linear: the
        clr     b                       ; previous block's `dry:` left it so)
        do      n7,>rtd_z ; CYCLES_AUX_LOOP
        move    b,x:(r4)+
        move    b,x:(r4)+
rtd_z:
rtd_ptr:
        move    a,x:(r7+$1d)            ; the print target (raw $66)
        move    x:(r7-$29),x1           ; x1 = the write offset AGAIN: the
                                        ; auto-gain block below reads it as
                                        ; "still valid from the address block
                                        ; above", and the latch used x1

'''

DL_STAMP = r'''; ---- RETURNS: stamp this buffer for core 0's hook, $5a0000 | write offset,
; in returns mode (every call: the hook reads it three buffers on, when both
; halves of a split block are long in). One writer (here), one clearer (the
; hook), three buffers apart.
        move    x:(r7+$1c),a
        tst     a
        beq     rtd_nost
        move    x:(r7-$29),a            ; write offset (0..112)
        move    a,x0
        asr     #$4,a,a                 ; the buffer's index
        move    #>$30200,b
        add     a,b
        move    b,r5                    ; its stamp word
        move    #>$5a0000,a
        add     x0,a                    ; | the write offset
        move    a,y:(r5)
rtd_nost:

'''

def transform(name: str, src: str) -> str:
    """Route one selected server; other source sections are untouched."""
    if name == "REVERB SERVER":
        src = _once(src, "bus_off_done:\n", RV_LATCH + "bus_off_done:\n")
        src = _once(src, "        do      n7,>rvend\n", RV_PREFILL + "        do      n7,>rvend\n")
        src = _once(src, "        move    x:(r7+$09),a            ; WET, ramped per sample: + this", """        move    n4,r4                   ; this sample's return-buffer pair
        lua     (r0+$2),r0              ; dry cursor advances independently
        move    x:(r7+$09),a            ; WET, ramped per sample: + this""")
        for a,b in (
            ("        move    x:(r0),x0               ; dry L, still in place", "        move    y:(r4),x0               ; dry L or zero from the prefill"),
            ("        move    a,x:(r0)+               ; L in place -- dry + wet; r0 on to R", "        move    a,y:(r4)+               ; L: dry+wet or independent wet"),
            ("        move    x:(r0),x0               ; dry R, still in place", "        move    y:(r4),x0               ; dry R or zero from the prefill"),
            ("        move    a,x:(r0)+               ; R in place -- dry + wet; r0 on to\n                                        ; the next frame (n0 is not used)", "        move    a,y:(r4)+               ; R: dry+wet or independent wet\n        move    r4,n4                   ; next return-buffer pair"),
        ):
            src = _once(src, a, b)
        return _once(src, "rvend:\n", "rvend:\n" + RV_END)
    if name == "DELAY SERVER":
        src = _once(src, "; ---- bus auto-gain: resolve 1/sqrt(N)", DL_LATCH + "; ---- bus auto-gain: resolve 1/sqrt(N)")
        src = _once(src, "        do      n7,>dlyend", """        move    n7,x0                   ; the sample count, preserved separately
        move    x0,x:(r7+$1f)           ; raw $68
        move    x:(r7+$1d),n7           ; raw $66: print target
        do      x0,>dlyend ; CYCLES_SAMPLE_LOOP
                                        ; n7 carries the print target""")
        src = _once(src, "        move    x:(r7+$32),x0           ; wet L = fL", "        move    n7,r4                   ; dry block or independent return buffer\n        move    x:(r7+$32),x0           ; wet L = fL")
        for a,b in (
            ("        move    x:(r0),b                ; dry L, still in place", "        move    x:(r4),b                ; dry L or zero from the prefill"),
            ("        move    b,x:(r0)                ; L in place -- dry + wet*WET", "        move    b,x:(r4)+               ; L: dry+wet or independent wet"),
            ("        move    x:(r0+n0),a             ; dry R", "        move    x:(r4),a                ; dry R or zero from the prefill"),
            ("        move    a,x:(r0+n0)             ; R in place -- dry + wet*WET", "        move    a,x:(r4)+               ; R: dry+wet or independent wet\n        move    r4,n7                   ; next return-buffer pair"),
        ):
            src = _once(src, a, b)
        src = _once(src, "dlyend:\n", "dlyend:\n        move    x:(r7+$1f),n7           ; restore dispatcher's sample count\n")
        return _once(src, "; ---- save both phases, restore the M registers", DL_STAMP + "; ---- save both phases, restore the M registers")
    return src
