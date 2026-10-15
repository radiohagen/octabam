    .include "remix.inc"
/* CHRD travels beside native MIDI staging/pending locks, never in them.
 * The builder resolves the exact bank/pattern/track/step before scheduling.
 * A pending record retains explicit quality or the unlocked sentinel and
 * its captured Part context. Inheritance resolves from that Part at fire,
 * never from the UI bank or the currently selected live chord.
 */
    .text
    .global ch_stage_fill,ch_stage_copy_a,ch_stage_copy_b,ch_pending_fire
ch_stage_fill:
    lea -28(%sp),%sp
    movem.l %d0-%d4/%a0-%a1,(%sp)
    move.l %d3,%d2 /* track before native multiply below */
    move.l %d7,%d3 /* exact scheduled step */
    move.l 76(%sp),%d0 /* bank: original sp+48 */
    move.l %a3,%d1
    move.l 88(%sp),%d4
    jsr hd_stage
    jsr ch_lock_ptr
    moveq #-1,%d4
    tst.l %a0
    beq.s .stage_context
    move.b (%a0),%d4
.stage_context:
    jsr ch_pattern_context
    move.l 88(%sp),%d1 /* pending slot: original sp+60 */
    lea ch_staged,%a0
    lea ch_staged_context,%a1
    tst.l %d1
    bmi.s .stage_ready
    cmpi.l #3,%d1
    bhi.s .stage_done
    lsl.l #3,%d1
    lea ch_pending,%a0
    adda.l %d1,%a0
    lea ch_pending_context,%a1
    adda.l %d1,%a1
.stage_ready:
    move.b %d4,(%a0,%d2.l)
    move.b %d0,(%a1,%d2.l)
.stage_done:
    movem.l (%sp),%d0-%d4/%a0-%a1
    lea 28(%sp),%sp
    move.l %d3,%d1
    lsl.l #5,%d1
    lea (%a5,%d1.l),%a0
    jmp 0x4009d188
ch_stage_copy_a:
    lea -8(%sp),%sp
    movem.l %d0/%a0,(%sp)
    move.l %d2,%d0
    jsr hd_stage_copy
    lea ch_staged,%a0
    move.b (%a0,%d2.l),%d0
    lea ch_pending,%a0
    move.b %d0,(%a0,%d2.l)
    lea ch_staged_context,%a0
    move.b (%a0,%d2.l),%d0
    lea ch_pending_context,%a0
    move.b %d0,(%a0,%d2.l)
    movem.l (%sp),%d0/%a0
    addq.l #8,%sp
    adda.l #0x46c78960,%a0
    jmp 0x4009b922
ch_stage_copy_b:
    lea -8(%sp),%sp
    movem.l %d0/%a0,(%sp)
    move.l %d1,%d0
    jsr hd_stage_copy
    lea ch_staged,%a0
    move.b (%a0,%d1.l),%d0
    lea ch_pending,%a0
    move.b %d0,(%a0,%d1.l)
    lea ch_staged_context,%a0
    move.b (%a0,%d1.l),%d0
    lea ch_pending_context,%a0
    move.b %d0,(%a0,%d1.l)
    movem.l (%sp),%d0/%a0
    addq.l #8,%sp
    adda.l #0x46c78960,%a0
    jmp 0x4009c10e
/* Publish before the native pending copy. MIDI SCENES owns that copy's
 * 0x400a19da boundary; leave its hook and continuation untouched. */
    .global ch_pending_entry
ch_pending_entry:
    move.l 136(%sp),%d6
    move.l %d6,48(%sp)
    subq.l #8,%sp
    movem.l %a0-%a1,(%sp)
    move.l %d0,%a0
    move.l %d6,%a1
    bsr.w ch_pending_publish
    movem.l (%sp),%a0-%a1
    addq.l #8,%sp
    jmp 0x400a19d6
/* Direct linked-test entry for the native copy ABI. */
ch_pending_fire:
    bsr.w ch_pending_publish
    movem.l (%a0),%d1-%d4/%d6-%d7/%a4-%a5
    movem.l %d1-%d4/%d6-%d7/%a4-%a5,(%a1)
    jmp 0x400a19e2
ch_pending_publish:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %a0,%d0
    subi.l #0x46c78960,%d0
    lsr.l #5,%d0
    cmpi.l #31,%d0
    bhi.s .fire_done
    jsr hd_fire
    move.l %d0,%d1
    lea ch_pending,%a0
    move.b (%a0,%d0.l),%d0
    andi.l #255,%d0
    cmpi.l #7,%d0
    bls.s .fire_quality
    lea ch_pending_context,%a0
    move.b (%a0,%d1.l),%d1
    andi.l #255,%d1
    move.l %d5,%d0
    jsr ch_base_at
.fire_quality:
    lea ch_sequence_quality,%a0
    move.b %d0,(%a0,%d5.l)
.fire_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
    .balign 4
ch_staged: .space 8,255
ch_pending: .space 32,255
ch_staged_context: .space 8,255
ch_pending_context: .space 32,255
