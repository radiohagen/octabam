/* Receiver register policy. Settings come from the playing native Part.
 * Keep absolute source pitches independently of the historical bass latch.
 * Register selection precedes receiver TRAN and Harmony root snapping.
 */
    .text
    .global bf_register,bf_reg_change,bf_mode_get,bf_oct_get
/* d0=ultimate source track, d1=receiver -> d0=signed pitch or 256 (unknown).
 * A relative octave can temporarily go outside MIDI; TRAN may bring it back.
 * All other registers are preserved; callers validate after adding TRAN.
 */
bf_register:
    lea -20(%sp),%sp
    movem.l %d1-%d4/%a0,(%sp)
    cmpi.l #7,%d0
    bhi.w .reg_unknown
    cmpi.l #7,%d1
    bhi.w .reg_unknown
    move.l %d0,%d4
    move.l %d1,%d0
    jsr bf_mode_play
    cmpi.l #1,%d0
    beq.s .reg_source
    lea bf_roots,%a0
    moveq #0,%d2
    move.b (%a0,%d4.l),%d2
    cmpi.l #127,%d2
    bhi.w .reg_unknown
    subi.l #36,%d2
    move.l %d1,%d0
    jsr bf_fixed_play
    bra.s .reg_octave
.reg_source:
    lea bf_pitches,%a0
    moveq #0,%d2
    move.b (%a0,%d4.l),%d2
    cmpi.l #127,%d2
    bhi.w .reg_unknown
    move.l %d1,%d0
    jsr bf_offset_play
.reg_octave:
    moveq #12,%d3
    muls.l %d3,%d0
    add.l %d2,%d0
    bra.s .reg_return
.reg_unknown:
    move.l #256,%d0
.reg_return:
    movem.l (%sp),%d1-%d4/%a0
    lea 20(%sp),%sp
    rts

/* UI octave follows MODE but retains both independent values in the Part. */
bf_oct_get:
    move.l %d1,-(%sp)
    move.l %d0,%d1
    jsr bf_mode_get
    tst.l %d0
    bne.s .oct_relative
    move.l %d1,%d0
    jsr bf_fixed_get
    bra.s .oct_done
.oct_relative:
    move.l %d1,%d0
    jsr bf_offset_get
.oct_done:
    move.l (%sp)+,%d1
    rts

/* d0 track,d1 control (0 mode,1 octave),d2 delta; preserves all registers. */
bf_reg_change:
    lea -28(%sp),%sp
    movem.l %d0-%d5/%a0,(%sp)
    cmpi.l #7,%d0
    bhi.w .change_done
    cmpi.l #1,%d1
    bhi.w .change_done
    move.l %d0,%d3
    moveq #0,%d4
    moveq #1,%d5
    tst.l %d1
    bne.s .change_octave
    jsr bf_mode_get
    lea bf_mode_set,%a0
    bra.s .change_clamp
.change_octave:
    jsr bf_mode_get
    tst.l %d0
    bne.s .change_relative
    move.l %d3,%d0
    jsr bf_fixed_get
    moveq #10,%d5
    lea bf_fixed_set,%a0
    bra.s .change_clamp
.change_relative:
    move.l %d3,%d0
    jsr bf_offset_get
    moveq #-2,%d4
    moveq #2,%d5
    lea bf_offset_set,%a0
.change_clamp:
    cmpi.l #16,%d2
    ble.s .change_low_delta
    moveq #16,%d2
.change_low_delta:
    cmpi.l #-16,%d2
    bge.s .change_add
    moveq #-16,%d2
.change_add:
    add.l %d2,%d0
    cmp.l %d4,%d0
    bge.s .change_max
    move.l %d4,%d0
.change_max:
    cmp.l %d5,%d0
    ble.s .change_store
    move.l %d5,%d0
.change_store:
    move.l %d0,%d1
    move.l %d3,%d0
    jsr (%a0)
.change_done:
    movem.l (%sp),%d0-%d5/%a0
    lea 28(%sp),%sp
    rts
