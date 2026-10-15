/* Native page/editor ABI adapters. Only NOTE-page slot A in HARM is owned. */
    .text
    .global hd_ui_owned,hd_encoder,hd_step_encoder,hd_step_push,hd_draw,hd_descriptor
hd_ui_owned: /* d1 slot -> d0 boolean; same volatile set as ch_ui_owned */
    moveq #0,%d0
    tst.l %d1
    bne.s .owned_return
    tst.l 0x80000012
    beq.s .owned_return
    tst.l 0x460d1684
    bne.s .owned_return
    move.l 0x460d175c,%a0
    tst.l %a0
    beq.s .owned_mode
    move.l 40(%a0),%d0
    cmpi.l #16,%d0
    beq.s .owned_mode
    /* The stock page-change notification is an 18-row nonmodal popup.
     * Native dispatch still routes its encoder gestures to the main page. */
    cmpi.l #18,%d0
    beq.s .owned_mode
    moveq #0,%d0
    rts
.owned_mode:
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
.owned_return:
    rts

.global hd_ui_disabled
/* Hidden D/E/F in HARM NOTE must not edit dormant native NOT2-4. */
hd_ui_disabled:
    moveq #0,%d0
    cmpi.l #3,%d1
    bcs.s .disabled_done
    cmpi.l #5,%d1
    bhi.s .disabled_done
    move.l %d1,-(%sp)
    moveq #0,%d1
    bsr.w hd_ui_owned
    move.l (%sp)+,%d1
    cmpi.l #1,%d0
    seq %d0
    andi.l #1,%d0
.disabled_done:
    rts

/* Modify the descriptor copy; NOTE mode also hides native NOT2-4. */
hd_descriptor:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l #0x44454700,%d0 /* DEG */
    move.l %d0,0x16(%a0)
    clr.w 0x1a(%a0)
    moveq #84,%d0
    move.l %d0,0x9a(%a0)
    move.l #hd_format,%d0
    move.l %d0,0xca(%a0)
    move.l #0x400467a4,%d0
    move.l %d0,0xfa(%a0)
    clr.l 0x12a(%a0)
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr mh_get
    cmpi.l #1,%d0
    bne.s .desc_done
    move.l 8(%sp),%a0
    move.l #0x2d2d2d00,%d0
    move.l %d0,0x28(%a0)
    move.l %d0,0x2e(%a0)
    move.l %d0,0x34(%a0)
    clr.w 0x2c(%a0)
    clr.w 0x32(%a0)
    clr.w 0x38(%a0)
    move.l 0x18e(%a0),%d0
    andi.l #0xff000fff,%d0
    move.l %d0,0x18e(%a0)
.desc_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

/* Returns degree in d0 and explicit lock in d5 bit 0. */
hd_draw:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    moveq #-1,%d0
    tst.l 0x460d173a
    beq.s .draw_get
    jsr 0x40041760
.draw_get:
    move.l %d0,-(%sp)
    jsr hd_ui_value_c
    addq.l #4,%sp
    bclr #0,%d5
    tst.l %d0
    bmi.s .draw_done
    btst #8,%d0
    beq.s .draw_done
    bset #0,%d5
    andi.l #255,%d0
.draw_done:
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts

hd_encoder:
    move.l 8(%sp),%d1
    moveq #0,%d0
    jsr mh_ui_delta
    clr.l -(%sp)
    clr.l -(%sp)
    move.l %d0,-(%sp)
    jsr hd_ui_edit_c
    lea 12(%sp),%sp
    tst.l %d0
    beq.s .encoder_done
    bsr.w .edit_finish
    jmp ch_ui_redraw
.encoder_done:
    rts
hd_step_push:
    move.l 8(%sp),%d0
    cmpi.l #1,%d0
    bne.s .encoder_done
    moveq #1,%d1
    moveq #0,%d0
    bra.s .step_edit
hd_step_encoder:
    move.l 8(%sp),%d1
    moveq #0,%d0
    jsr mh_ui_delta
    moveq #0,%d1
.step_edit:
    pea 1
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_ui_edit_c
    lea 12(%sp),%sp
    tst.l %d0
    beq.s .encoder_done
    bsr.s .edit_finish
    /* Rebuild stock indicators and use the native held-edit tail to place
     * trigless locks. Match its original editor frame exactly. */
    bsr.s .bitmaps
    lea -80(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40050ec2
.edit_finish:
    moveq #0,%d0
    move.b 0x80000002,%d0
    jsr ch_nv_save
    jmp ch_ui_dirty
.bitmaps:
    lea -8(%sp),%sp
    movem.l %d2-%d3,(%sp)
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    moveq #0,%d3
.bitmap_loop:
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    jsr 0x40033b3c
    addq.l #8,%sp
    addq.l #1,%d3
    cmpi.l #64,%d3
    bne.s .bitmap_loop
    movem.l (%sp),%d2-%d3
    addq.l #8,%sp
    rts
