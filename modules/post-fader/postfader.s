| POST FADER -- transient send gain and original participation.
| Derived from sanderlegit's PR 542; participation added 26 Oct 2026.
|
| The frame routine calls the mixer-gain publisher and then the per-track
| DSP record builder (measured, the stock sequence):
|
|   4000d0de  jsr    0x40004db8     | mixer gains -> *(0x80003c10): 4 halfwords
|                                   |   a track; halfword 1 = MAIN gain, the
|                                   |   level << 8 with mute and solo applied
|   4000d0e4  jsr    0x40004bd4     | records -> 0x80000110 + (*0x800000e0 << 9),
|                                   |   64 bytes a track; FX2 page-1 slots 0/1
|                                   |   at +24/+26 (value << 8 | fraction), the
|                                   |   FX2 id at +56
|
| The second call is detoured here: after the stock builder, every track
| whose FX2 is a selected bus consumer (id 0 only if it aliases SEND)
| has its slot-0/1 low 15 bits scaled by (L/128)^2, L
| the MAIN gain's high byte -- the mixer's own law (docs/firmware/LEVEL_LAW.md)
| -- in the DSP-bound record only. The Part, the panel and CC FEEDBACK's
| lanes keep the knob. Bit 15 marks ORIGINAL nonzero send participation,
| independently of LEVEL/mute/solo. The module-selected DSP path must mask
| bit 23 before arithmetic and use it for client counts. Muting a source
| retains its normalization share, so other sources' gains do not rise.
| Changing a SEND knob itself can still change membership. This is not the
| separate scene XLV curve or stock's split-aware per-sample mixer ramp.
| BusDelay's slot-1 low byte is TEMPO SYNC's held note (its cave
| writes +0x1b inside the builder): it is kept. RETURNS (T8) is not a send
| and is left alone.
|
| Measured under the port (29 Sep 2026, LEVEL 55 everywhere, T7 muted):
| c50 bytes 55, the mixer record's halfword 1 0x3700 on every track and 0 on
| the muted one; the records' +56 ids 6 9 9 9 7 9 9 1e.

        .include "remix.inc"           | ID_SEND, ID_DELAY, ID_VERB
        .set    RECORDS, 0x80000110
        .set    PING, 0x800000e0
        .set    MIXREC, 0x80003c10
        .set    BUILDER, 0x40004bd4

        .text
        .globl  pf_frame
pf_frame:
        jsr     BUILDER                 | the displaced call
        lea     -32(%sp),%sp
        movem.l %d0-%d5/%a0-%a1,(%sp)
        move.l  PING,%d0
        moveq   #9,%d1
        lsl.l   %d1,%d0
        movea.l %d0,%a0
        adda.l  #RECORDS,%a0            | this frame's records
        movea.l MIXREC,%a1              | this frame's mixer gains
        moveq   #14,%d3
        moveq   #8,%d5
pf_track:
        mvz.w   56(%a0),%d0             | the FX2 id
        .if PF_FALLBACK_SEND
        tst.l   %d0
        beq     pf_scale                | id 0 runs SEND's code
        .endif
        cmpi.l  #ID_SEND,%d0
        beq     pf_scale
        .ifdef ID_VERB
        cmpi.l  #ID_VERB,%d0
        beq     pf_scale
        .endif
        .ifdef ID_DELAY
        cmpi.l  #ID_DELAY,%d0
        beq     pf_scale
        .endif
        bra     pf_next
pf_scale:
        mvz.b   2(%a1),%d1              | L: the MAIN gain's high byte, 0..127
        mulu.w  %d1,%d1                 | L^2 < 16384
        mvz.w   24(%a0),%d2             | slot 0 (DEL)
        andi.l  #0x7fff,%d2             | original control, no stale tag
        move.l  %d2,%d4                 | participation before scaling
        mulu.l  %d1,%d2
        lsr.l   %d3,%d2                 | x (L/128)^2
        tst.l   %d4
        beq     pf_del_store
        ori.l   #0x8000,%d2
pf_del_store:
        move.w  %d2,24(%a0)
        mvz.w   26(%a0),%d2             | slot 1 (REV)
        andi.l  #0x7fff,%d2
        .ifdef ID_DELAY
        cmpi.l  #ID_DELAY,%d0
        bne     pf_rev
        move.l  %d2,%d4
        andi.l  #0xff,%d4               | BusDelay: keep TEMPO SYNC's note
        andi.l  #0x7f00,%d2
        move.l  %d2,%d0                 | note alone is not participation
        mulu.l  %d1,%d2
        lsr.l   %d3,%d2
        andi.l  #0x7f00,%d2
        or.l    %d4,%d2
        bra     pf_rev_tag
        .endif
pf_rev:
        move.l  %d2,%d0
        mulu.l  %d1,%d2
        lsr.l   %d3,%d2
pf_rev_tag:
        tst.l   %d0
        beq     pf_store
        ori.l   #0x8000,%d2
pf_store:
        move.w  %d2,26(%a0)
pf_next:
        lea     64(%a0),%a0
        addq.l  #8,%a1
        subq.l  #1,%d5
        bne     pf_track
        movem.l (%sp),%d0-%d5/%a0-%a1
        lea     32(%sp),%sp
        rts
