/* Base CHRD belongs to the native working Part. Explicit locks remain in
 * the pattern companion. No KITS or retained-default storage is involved.
 * Public entries preserve all registers except d0/condition codes. */
    .text
    .global ch_base_get,ch_base_play,ch_base_at,ch_base_set
    .global ch_pattern_context,ch_base_pattern

/* d0 track -> selected working Part's base quality. */
ch_base_get:
    lea -8(%sp),%sp
    movem.l %d0-%d1,(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp),%d0
    bsr.w ch_base_at
    move.l 4(%sp),%d1
    addq.l #8,%sp
    rts

/* d0 track -> this track's engine Part, never the UI selection. */
ch_base_play:
    lea -8(%sp),%sp
    movem.l %d0-%d1,(%sp)
    jsr mp_play_context
    move.l %d0,%d1
    move.l (%sp),%d0
    bsr.w ch_base_at
    move.l 4(%sp),%d1
    addq.l #8,%sp
    rts

/* d0 track, d1 explicit context -> quality; corrupt/unavailable -> TRI. */
ch_base_at:
    move.l %d2,-(%sp)
    moveq #18,%d2
    jsr mp_read
    cmpi.l #31,%d0
    bls.s .base_valid
    moveq #0,%d0
.base_valid:
    andi.l #7,%d0 /* SIZE shares the upper two bits; locks remain quality-only. */
    move.l (%sp)+,%d2
    rts

/* d0 track, d1 quality -> accepted. Native Part access owns dirty/mirror. */
ch_base_set:
    cmpi.l #7,%d1
    bhi.s .set_bad
    lea -16(%sp),%sp
    movem.l %d0-%d3,(%sp)
    move.l %d1,%d3
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp),%d0
    moveq #18,%d2
    jsr mp_read
    cmpi.l #31,%d0
    bls.s .set_packed_valid
    moveq #0,%d0
.set_packed_valid:
    andi.l #24,%d0
    or.l %d0,%d3
    move.l (%sp),%d0
    jsr mp_write
    movem.l 4(%sp),%d1-%d3
    lea 16(%sp),%sp
    rts
.set_bad:
    moveq #0,%d0
    rts

/* d0 bank, d1 pattern -> context, or -1. No selected-bank fallback. */
ch_pattern_context:
    cmpi.l #15,%d0
    bhi.s .context_bad
    cmpi.l #15,%d1
    bhi.s .context_bad
    lea -12(%sp),%sp
    movem.l %d2-%d3/%a0,(%sp)
    move.l %d0,%d2
    move.l #0x9b340,%d3
    mulu.l %d3,%d0
    lea 0x400e21e0,%a0
    adda.l %d0,%a0
    move.l #0x8ed8,%d0
    mulu.l %d1,%d0
    adda.l %d0,%a0
    adda.l #0x8e57,%a0
    moveq #0,%d0
    move.b (%a0),%d0
    cmpi.l #3,%d0
    bhi.s .context_invalid
    lsl.l #2,%d2
    add.l %d2,%d0
    bra.s .context_done
.context_invalid:
    moveq #-1,%d0
.context_done:
    movem.l (%sp),%d2-%d3/%a0
    lea 12(%sp),%sp
    rts
.context_bad:
    moveq #-1,%d0
    rts

/* d0 bank, d1 pattern, d2 track -> that pattern's inherited quality. */
ch_base_pattern:
    move.l %d1,-(%sp)
    bsr.w ch_pattern_context
    move.l %d0,%d1
    move.l %d2,%d0
    bsr.w ch_base_at
    move.l (%sp)+,%d1
    rts
