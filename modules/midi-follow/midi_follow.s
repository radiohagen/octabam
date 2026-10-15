/* OS 1.40C. Routing settings belong to native Parts; root history is volatile. */
    .text
    .include "remix.inc"
    .global bf_capture, bf_note, bf_roots, bf_pre_capture
    .global bf_encoder, bf_draw_value, bf_format, bf_select

/* Before the stock output loop: latch eligible ordinary triggers for ALL
 * tracks, so a low-numbered follower sees a high-numbered source this tick.
 * Arp-only ticks are still captured at bf_capture after stock's arp gates.
 * The original NOTE lanes have already received this tick's parameter locks.
 * A muted source still supplies roots. Only the stock output loop applies
 * track mute: capturing a root neither transmits nor owns a MIDI note.
 */
bf_pre_capture:
    lea -36(%sp),%sp
    movem.l %d0-%d3/%d7/%a0-%a1/%a4-%a5,(%sp)
    moveq #0,%d7
    lea 0x46c76dc0,%a5
    lea 0x46c76dc0,%a4
.pre_loop:
    move.l -42(%fp),%d0
    btst %d7,%d0
    beq.s .pre_next
    lea 0x80006676,%a0
    move.b (%a0,%d7.l),%d0
    cmpi.b #0xff,%d0
    beq.s .pre_next
    lea 0x8000666e,%a0
    move.b (%a0,%d7.l),%d0
    cmpi.b #0xff,%d0
    beq.s .pre_next
    tst.b 32(%a4)
    beq.s .pre_next
    tst.b 0x221(%a5)
    beq.s .pre_next
    moveq #0,%d1
    move.b 49(%a4),%d1
    beq.s .pre_latch
    move.l %d1,%d0
    subq.l #1,%d0
    lsr.l #1,%d0
    btst #0,%d1
    beq.s .minor
    moveq #12,%d1
    bra.s .rotate
.minor:
    moveq #21,%d1
.rotate:
    sub.l %d0,%d1
.pre_latch:
    bsr.w bf_latch
.pre_next:
    lea 32(%a5),%a5
    lea 68(%a4),%a4
    addq.l #1,%d7
    cmpi.l #8,%d7
    bne.w .pre_loop
.pre_response:
    move.l -42(%fp),%d0
    moveq #0,%d1
    move.b -37(%fp),%d1
    jsr bf_response_tick
.pre_restore:
    movem.l (%sp),%d0-%d3/%d7/%a0-%a1/%a4-%a5
    lea 36(%sp),%sp
    lea 0x80006676,%a0
    jmp 0x4009f98c

/* d7 track, a5 live NOTE lane - 0x220, fp@(-64) scale rotation. */
bf_capture:
    lea -16(%sp),%sp
    movem.l %d0-%d2/%a0,(%sp)
    .ifdef HAVE_HARMONY
    move.l %d7,%d0
    jsr mh_active
    andi.l #3,%d0
    bne.s .capture_done /* Harmony keyboard roots must survive arp-only ticks. */
    /* HARM OFF / KEY OFF live pools also have a root published by the
     * keyboard. Never replace it with the unrelated stored NOTE lane. */
    move.l %d7,%d0
    lsl.l #2,%d0
    add.l %d7,%d0
    add.l %d0,%d0
    lea 0x46c77b1e,%a0
    move.b (%a0,%d0.l),%d1
    cmpi.b #1,%d1
    beq.s .capture_done
    .endif
    move.l -64(%fp),%d1
    bsr.w bf_latch
.capture_done:
    movem.l (%sp),%d0-%d2/%a0
    lea 16(%sp),%sp
    move.l %d7,%d4
    lsl.l #2,%d4
    move.b %d4,-43(%fp)
    jmp 0x4009fb08

/* Original chord NOTE, never arp scratch; d1 = stock scale rotation.
 * Clobbers d0-d2/a0 only. Transpose arithmetic matches stock byte wrapping.
 */
bf_latch:
    clr.l %d0
    move.b 0x220(%a5),%d0
    bmi.w .latch_return
    .ifdef HAVE_HARMONY
    move.l %d1,-(%sp)
    move.l %d7,%d1
    jsr mh_prepare
    move.l (%sp)+,%d1
    .ifdef HAVE_HARMONY
    cmpi.l #127,%d0
    bhi.w .latch_return
    .endif
    move.l %d0,-(%sp)
    move.l %d1,-(%sp)
    move.l %d7,%d0
    jsr mh_active
    andi.l #3,%d0
    move.l (%sp)+,%d1
    tst.l %d0
    beq.s .latch_native_scale
    clr.l %d1
.latch_native_scale:
    move.l (%sp)+,%d0
    .endif
    clr.l %d2
    move.b 0x22c(%a5),%d2
    add.l %d2,%d0
    subi.l #64,%d0
    lea 0x46c7a124,%a0
    clr.l %d2
    move.b (%a0,%d7.l),%d2
    add.l %d2,%d0
    andi.l #255,%d0
    tst.b %d0
    bmi.w .latch_return
    .ifdef HAVE_SCALES
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    .ifdef HAVE_HARMONY
    move.l %d7,%d0
    jsr mh_active
    tst.l %d0
    bne.s .latch_harmony_restore
    .endif
    move.l %d7,%d0
    jsr ms_raw
    cmpi.l #24,%d0
    bls.s .latch_stock_restore
    move.l %d0,%d1
    move.l (%sp)+,%d0
    jsr ms_snap
    addq.l #4,%sp
    bra.s .root_mod
.latch_harmony_restore:
    move.l (%sp)+,%d0
    move.l (%sp)+,%d1
    bra.s .root_mod
.latch_stock_restore:
    move.l (%sp)+,%d0
    move.l (%sp)+,%d1
    .endif
    tst.l %d1
    ble.s .root_mod
    add.l %d0,%d1
.scale_mod:
    cmpi.l #12,%d1
    blt.s .scale_apply
    subi.l #12,%d1
    bra.s .scale_mod
.scale_apply:
    lea 0x400d80a0,%a0
    move.l (%a0,%d1.l*4),%d2
    add.l %d2,%d0
    andi.l #255,%d0
    tst.b %d0
    bmi.w .latch_return
.root_mod:
    .ifdef HAVE_HARMONY
    move.l %d1,-(%sp)
    move.l %d7,%d1
    jsr mh_quant /* Root snap is independent of the selected chord quality. */
    move.l (%sp)+,%d1
    .endif
    lea bf_pitches,%a0
    move.b %d0,(%a0,%d7.l) /* retain octave before the legacy bass reduction */
.root_reduce:
    cmpi.l #12,%d0
    blt.s .latch
    subi.l #12,%d0
    bra.s .root_reduce
.latch:
    addi.l #36,%d0
    lea bf_roots,%a0
    move.b %d0,(%a0,%d7.l)
.latch_return:
    rts

/* d7 track, d4 chord slot, a2 scratch pitch. The same scratch byte is
 * copied by stock into the release record, so old held notes release safely.
 * Chains resolve to the ultimate source; bounded defensively to eight hops.
 */
bf_note:
    jsr bf_response_adjust
    jsr bf_response_observe
    lea -16(%sp),%sp
    movem.l %d0-%d2/%a0,(%sp)
    .ifdef HAVE_HARMONY
    move.l %d7,%d0
    jsr mh_active
    andi.l #3,%d0
    bne.w .restore /* Harmony has already generated the follower chord before arp. */
    .endif
    tst.b (%a2)
    bmi.s .restore
    move.l %d7,%d0
    jsr bf_source_resolve
    cmp.l %d7,%d0
    beq.s .restore
.resolved:
    move.l %d7,%d1
    jsr bf_register
    cmpi.l #256,%d0
    beq.s .restore
    tst.l %d4
    bne.s .follower_extra
    /* TRAN is the follower's signed semitone offset (including step locks).
     * Read the original live lane; scratch has already been transposed and
     * scale-corrected by stock. Do not add that processing a second time.
     */
    moveq #0,%d1
    move.b 0x22c(%a5),%d1
    subi.l #64,%d1
    add.l %d1,%d0
    cmpi.l #127,%d0
    bhi.s .follower_extra      /* also rejects negative pitches, no wrapping */
    move.b %d0,(%a2)
    bra.s .restore
.follower_extra:
    move.b #0xff,(%a2)
.restore:
    movem.l (%sp),%d0-%d2/%a0
    lea 16(%sp),%sp
    move.b (%a2),%d1
    bmi.s .skip
    jmp 0x4009fb86
.skip:
    jmp 0x4009fd2a

/* NOTE SETUP D handler: same (encoder, signed delta) ABI as stock.
 * One step per detent, skipping self/cycles; no stock staged parameter writes.
 */
bf_encoder:
    move.l 4(%sp),%d0
    cmpi.l #3,%d0
    beq.s .encoder_follow
    jmp 0x4003a8e8 /* Native CHAN/BANK/PROG/SBNK, or Harmony's F wrapper. */
.encoder_follow:
    move.l 8(%sp),%d1
    bsr.w bf_ui_delta
    move.l %d0,%d1
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    bsr.w bf_select
    jmp 0x40036548              /* stock NOTE SETUP redraw */

/* d0 = track 0..7, d1 = signed detents. Other nonvolatile regs preserved.
 * Uses only caller-saved d0/d1/a0/a1 plus saved d2-d5.
 */
bf_select:
    lea -16(%sp),%sp
    movem.l %d2-%d5,(%sp)
    cmpi.l #7,%d0
    bhi.w .select_return
    move.l %d0,%d2
    move.l %d1,%d3
    beq.w .select_return
    moveq #1,%d4
    tst.l %d3
    bgt.s .direction
    moveq #-1,%d4
    neg.l %d3
.direction:
    /* At most eight usable values; huge/coalesced deltas saturate. */
    cmpi.l #8,%d3
    bls.s .bounded
    moveq #8,%d3
.bounded:
    move.l %d2,%d0
    jsr bf_source_get
.next_choice:
    add.l %d4,%d0
    bmi.s .select_return
    cmpi.l #8,%d0
    bhi.s .select_return
    tst.l %d0
    beq.s .accept
    move.l %d0,%d1
    moveq #8,%d5
.check_cycle:
    subq.l #1,%d1
    cmp.l %d2,%d1
    beq.s .next_choice
    cmpi.l #7,%d1
    bhi.s .next_choice
    move.l %d0,-(%sp)
    move.l %d1,%d0
    jsr bf_source_get
    move.l %d0,%d1
    move.l (%sp)+,%d0
    tst.l %d1
    beq.s .accept
    subq.l #1,%d5
    bne.s .check_cycle
    bra.s .next_choice
.accept:
    move.l %d0,-(%sp)
    move.l %d0,%d1
    move.l %d2,%d0
    jsr bf_source_set
    move.l (%sp)+,%d0
    subq.l #1,%d3
    bne.s .next_choice
.select_return:
    movem.l (%sp),%d2-%d5
    lea 16(%sp),%sp
    rts

/* NOTE SETUP's own drawer, slot D only. Never alter its staged value. */
bf_draw_value:
    move.l (%a5),%d3
    cmpi.l #3,%d4
    bne.s .draw_return
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    andi.l #7,%d0
    jsr bf_source_get
    move.l %d0,%d3
    move.l %d3,48(%sp)         /* comparison value: no false pending-edit mark */
.draw_return:
    move.l %d4,%d2
    moveq #3,%d0
    jmp 0x4003667a

/* Formatter ABI (char *buf, int value), bounded output max three chars. */
bf_format:
    move.l 4(%sp),%a0
    move.l 8(%sp),%d0
    tst.l %d0
    beq.s .fmt_off
    cmpi.l #8,%d0
    bhi.s .fmt_off
    move.b #84,(%a0)+
    addi.l #48,%d0
    move.b %d0,(%a0)+
    clr.b (%a0)
    rts
.fmt_off:
    move.b #79,(%a0)+
    move.b #70,(%a0)+
    move.b #70,(%a0)+
    clr.b (%a0)
    rts

    .balign 2
bf_roots:
    .space 8,0xff              /* no eligible source yet: pass through */

    .global bf_pitches
bf_pitches: .space 8,0xff /* absolute source roots, independently of receiver register */

/* d0 physical encoder, d1 raw movement -> d0 choice delta.
 * Stock fixed-point detent accumulator; four counts per choice, at most one
 * choice per report. No push acceleration for these small enumerations. */
    .global bf_ui_delta
bf_ui_delta:
    cmpi.l #4,%d1
    ble.s .ui_delta_low
    moveq #4,%d1
.ui_delta_low:
    cmpi.l #-4,%d1
    bge.s .ui_delta_accumulate
    moveq #-4,%d1
.ui_delta_accumulate:
    pea 1024
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr 0x40032510
    lea 12(%sp),%sp
    rts
