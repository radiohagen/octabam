    .include "remix.inc"
/* Dedicated NOTE-page CHRD presentation. The descriptor is a runtime copy
 * of the composed NOTE descriptor. No native Part or NOT2-4 byte is edited.
 */
    .text
    .global ch_descriptor,ch_draw_value,ch_encoder,ch_step_encoder
    .global ch_ui_dirty,ch_ui_redraw
ch_descriptor:
    tst.l 8(%fp)
    bne.w .desc_return
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    tst.l %d0
    beq.w .desc_stock
    lea 0x400d3e3e,%a0
    lea ch_note_descriptor,%a1
    move.l #402/2,%d0
.desc_copy:
    move.w (%a0)+,(%a1)+
    subq.l #1,%d0
    bne.s .desc_copy
    lea ch_note_descriptor,%a0
    jsr hd_descriptor
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    cmpi.l #1,%d0
    beq.w .desc_degree_return
    lea ch_note_descriptor,%a0
    move.l #0x43485244,%d0
    move.l %d0,0x28(%a0) /* CHRD */
    moveq #0,%d0
    move.b 0x80000002,%d0
    lea ch_lock_status,%a1
    move.b (%a1,%d0.l),%d0
    cmpi.b #2,%d0
    bcs.s .desc_status_ok
    move.l #0x43482100,%d0 /* CH!: inspect CHORD PLAY guide */
    move.l %d0,0x28(%a0)
.desc_status_ok:
    clr.w 0x2c(%a0)
    move.l #0x2d2d2d00,%d0
    move.l %d0,0x2e(%a0)
    clr.w 0x32(%a0)
    move.l #0x2d2d2d00,%d0
    move.l %d0,0x34(%a0)
    clr.w 0x38(%a0)
    clr.l 0x76(%a0)
    moveq #8,%d0
    move.l %d0,ch_note_descriptor+0xa6
    move.l #ch_quality_format,%d0
    move.l %d0,ch_note_descriptor+0xd6
    move.l #0x400467a4,%d0
    move.l %d0,ch_note_descriptor+0x106
    clr.l ch_note_descriptor+0x136
    move.l ch_note_descriptor+0x18e,%d0
    andi.l #0xff00ffff,%d0
    move.l %d0,ch_note_descriptor+0x18e /* disable E/F only */
.desc_degree_return:
    move.l #ch_note_descriptor,%d0
    bra.s .desc_return
.desc_stock:
    move.l #0x400d3e3e,%d0
.desc_return:
    move.l %d0,-80(%fp)
    move.l %d0,%a0
    jmp 0x4004e1fc

/* Main NOTE draw, after native lock/default selection, before widget.
 * a4 is slot, d0 value, d5 widget flags (bit0 explicit lock).
 */
ch_draw_value:
    lea -24(%sp),%sp
    movem.l %d0-%d3/%a0-%a1,(%sp)
    tst.l 8(%fp)
    bne.w .draw_restore
    tst.l %a4
    bne.s .draw_chord
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    tst.l %d0
    beq.w .draw_restore
    jsr hd_draw
    move.l %d0,(%sp)
    bra.w .draw_restore
.draw_chord:
    cmpa.l #3,%a4
    bne.w .draw_restore
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    cmpi.l #2,%d0
    bcs.w .draw_restore
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    move.l %d2,%d0 /* The knob shows its Part default, never a live override. */
    jsr ch_base_get
    bclr #0,%d5 /* Native NOT2 locks must not highlight the CHRD default. */
    tst.l 0x460d173a /* lock-inspection flag */
    beq.s .draw_live
    jsr 0x40041760
    tst.l %d0
    bpl.s .draw_step
    move.l %d2,%d0
    jsr ch_base_get
    bra.s .draw_live
.draw_step:
    move.l %d0,%d3
    moveq #0,%d1
    move.b 0x100b14d0,%d1
    moveq #0,%d0
    move.b 0x80000002,%d0
    jsr ch_lock_ptr
    moveq #0,%d0
    bclr #0,%d5
    move.l %a0,%d1
    beq.s .draw_default
    move.b (%a0),%d0
    cmpi.l #7,%d0
    bls.s .draw_locked
.draw_default:
    move.l %d2,%d0
    jsr ch_base_get
    bra.s .draw_live
.draw_locked:
    bset #0,%d5
.draw_live:
    move.l %d0,(%sp)
.draw_restore:
    movem.l (%sp),%d0-%d3/%a0-%a1
    lea 24(%sp),%sp
    move.l -52(%fp),%a1
    move.l 48(%a1),%a0
    jmp 0x4004e38a

/* Both stock editors take (slot, delta). Only main NOTE D/E/F are owned. */
ch_encoder:
    move.l 4(%sp),%d1
    jsr hd_ui_owned
    tst.l %d0
    beq.s .ch_encoder_ordinary
    jmp hd_encoder
.ch_encoder_ordinary:
    move.l 4(%sp),%d1
    jsr hd_ui_disabled
    tst.l %d0
    bne.w .edit_done
    move.l 4(%sp),%d1
    bsr.w ch_ui_owned
    tst.l %d0
    bne.s .live_owned
    lea -48(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40055010
.live_owned:
    move.l 4(%sp),%d0
    cmpi.l #3,%d0
    bne.s .edit_done
    lea -16(%sp),%sp
    movem.l %d2-%d3/%a2-%a3,(%sp)
    moveq #3,%d0
    move.l 24(%sp),%d1
    jsr mh_ui_delta
    move.l %d0,%d3
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    move.l %d2,%d0
    jsr ch_base_get
    move.l %d3,%d1
    bsr.w ch_clamp_delta
    move.l %d0,%d1
    move.l %d2,%d0
    jsr ch_base_set
    move.l %d2,%d1
    jsr ch_refresh_quality
    movem.l (%sp),%d2-%d3/%a2-%a3
    lea 16(%sp),%sp
    bra.w ch_ui_redraw
.edit_done:
    rts

ch_step_encoder:
    move.l 4(%sp),%d1
    jsr hd_ui_owned
    tst.l %d0
    beq.s .ch_step_encoder_ordinary
    jmp hd_step_encoder
.ch_step_encoder_ordinary:
    move.l 4(%sp),%d1
    jsr hd_ui_disabled
    tst.l %d0
    bne.w .edit_done
    move.l 4(%sp),%d1
    bsr.w ch_ui_owned
    tst.l %d0
    bne.s .steps_owned
    lea -80(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x400508ec
.steps_owned:
    move.l 4(%sp),%d0
    cmpi.l #3,%d0
    bne.s .edit_done
    lea -32(%sp),%sp
    movem.l %d2-%d7/%a2-%a3,(%sp)
    moveq #3,%d0
    move.l 40(%sp),%d1
    jsr mh_ui_delta
    move.l %d0,%d7
    tst.l ch_toggle_active
    bne.s .steps_edit
    tst.l %d7
    beq.w .steps_no_change
.steps_edit:
    jsr ch_lock_init
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    moveq #0,%d5
    move.w 0x460d174a,%d5
    moveq #0,%d6
.step_loop:
    btst %d6,%d5
    beq.s .step_next
    moveq #0,%d0
    move.b 0x80000002,%d0
    moveq #0,%d1
    move.b 0x100b14d0,%d1
    move.l %d6,%d3
    add.l 0x460d174c,%d3
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .step_next
    move.l %a0,%a2
    moveq #0,%d0
    move.b (%a2),%d0
    tst.l ch_toggle_active
    beq.s .step_turn
    cmpi.l #7,%d0
    bhi.s .step_lock_default
    moveq #-1,%d0
    bra.s .step_store
.step_lock_default:
    move.l %d2,%d0
    jsr ch_base_get
    bra.s .step_store
.step_turn:
    cmpi.l #7,%d0
    bls.s .step_value
    move.l %d2,%d0
    jsr ch_base_get
.step_value:
    move.l %d7,%d1
    bsr.w ch_clamp_delta
 .step_store:
    move.b %d0,(%a2)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    jsr 0x40033b3c /* native lock bitmap plus dedicated CHRD */
    addq.l #8,%sp
.step_next:
    addq.l #1,%d6
    cmpi.l #16,%d6
    bne.s .step_loop
    moveq #0,%d0
    move.b 0x80000002,%d0
    jsr ch_nv_save
    jsr ch_ui_dirty
    movem.l (%sp),%d2-%d7/%a2-%a3
    lea 32(%sp),%sp
    /* Native tail marks this as a held-step edit and places trigless locks
     * where necessary. Its frame must match the displaced stock prologue. */
    lea -80(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40050ec2

.steps_no_change:
    movem.l (%sp),%d2-%d7/%a2-%a3
    lea 32(%sp),%sp
    rts

/* d1 = NOTE-page slot. */
ch_ui_owned:
    moveq #0,%d0
    tst.l 0x80000012
    beq.s .owned_done
    move.l 0x460d175c,%a0
    tst.l %a0
    beq.s .owned_page
    move.l 40(%a0),%d0 /* the held-step inspection strip has 16 rows */
    cmpi.l #16,%d0
    beq.s .owned_page
    /* Main-page input remains active under the page-change notification. */
    cmpi.l #18,%d0
    beq.s .owned_page
    moveq #0,%d0 /* full NOTE SETUP and other modal editors keep their controls */
    rts
.owned_page:
    moveq #0,%d0
    tst.l 0x460d1684
    bne.s .owned_done
    cmpi.l #3,%d1
    bcs.s .owned_done
    cmpi.l #5,%d1
    bhi.s .owned_done
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    cmpi.l #2,%d0
    scc %d0
    andi.l #1,%d0
.owned_done:
    rts
ch_clamp_delta:
    cmpi.l #7,%d1
    ble.s .clamp_low
    moveq #7,%d1
.clamp_low:
    cmpi.l #-7,%d1
    bge.s .clamp_add
    moveq #-7,%d1
.clamp_add:
    add.l %d1,%d0
    bpl.s .clamp_high
    moveq #0,%d0
.clamp_high:
    cmpi.l #7,%d0
    ble.s .clamp_done
    moveq #7,%d0
.clamp_done:
    rts
ch_ui_dirty:
    move.l 0x46c82456,%a0
    move.l #0x9b332,%d0
    moveq #1,%d1
    move.l %d1,(%a0,%d0.l)
    move.l %d1,0x100f8598
    jmp 0x40027e00
ch_ui_redraw:
    pea -1
    jsr 0x4004d948
    addq.l #4,%sp
    rts
    .bss
    .balign 4
ch_note_descriptor: .space 402

    .text
    .global ch_step_push
ch_step_push:
    move.l 4(%sp),%d1
    subi.l #56,%d1
    jsr hd_ui_owned
    tst.l %d0
    beq.s .ch_step_push_ordinary
    jmp hd_step_push
.ch_step_push_ordinary:
    move.l 4(%sp),%d1
    subi.l #56,%d1
    jsr hd_ui_disabled
    tst.l %d0
    bne.w .push_done
    move.l 4(%sp),%d1
    subi.l #56,%d1
    bsr.w ch_ui_owned
    tst.l %d0
    beq.s .push_stock
    move.l 4(%sp),%d0
    cmpi.l #59,%d0
    bne.s .push_done
    move.l 8(%sp),%d0
    cmpi.l #1,%d0
    bne.s .push_done
    move.l %d0,ch_toggle_active
    clr.l -(%sp)
    pea 3
    bsr.w ch_step_encoder
    addq.l #8,%sp
    clr.l ch_toggle_active
.push_done:
    rts
.push_stock:
    lea -76(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40050414
    .balign 4
ch_toggle_active: .long 0
