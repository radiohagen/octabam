    .text
    .global ha_shift,ha_sounded,ha_start_a,ha_start_b
/* d0 root pitch, d1 track, d2 context. Preserve all except result d0. */
ha_shift:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr ha_shift_c
    lea 12(%sp),%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
/* d0 track; no register changes. */
ha_sounded:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr ha_sounded_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
ha_start_a:
    bsr.s .ha_transport
    move.l %d0,0x800065b8
    jmp 0x4009c3da
ha_start_b:
    bsr.s .ha_transport
    move.l %d0,0x800065b8
    jmp 0x4009c4da
.ha_transport:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr ha_transport_c
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

    .global ha_ui_owned,ha_descriptor,ha_draw,ha_encoder,ha_step_encoder,ha_step_push
ha_ui_owned:
    moveq #0,%d0
    cmpi.l #4,%d1
    bne.s .ha_owned_done
    move.l %d1,-(%sp)
    moveq #0,%d1
    jsr hd_ui_owned
    move.l (%sp)+,%d1
.ha_owned_done:
    rts
ha_descriptor:
    move.l #0x41434300,%d0
    move.l %d0,0x2e(%a0)
    clr.w 0x32(%a0)
    moveq #16,%d0
    move.l %d0,0xaa(%a0)
    move.l #ha_format_c,%d0
    move.l %d0,0xda(%a0)
    move.l #0x400467a4,%d0
    move.l %d0,0x10a(%a0)
    clr.l 0x13a(%a0)
    move.l 0x18e(%a0),%d0
    ori.l #0x00010000,%d0
    move.l %d0,0x18e(%a0)
    rts
ha_draw:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    moveq #-1,%d0
    tst.l 0x460d173a
    beq.s .ha_draw_get
    jsr 0x40041760
.ha_draw_get:
    move.l %d0,-(%sp)
    jsr ha_ui_value_c
    addq.l #4,%sp
    bclr #0,%d5
    btst #8,%d0
    beq.s .ha_draw_done
    bset #0,%d5
    andi.l #255,%d0
.ha_draw_done:
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
ha_encoder:
    move.l 8(%sp),%d1
    moveq #4,%d0
    jsr mh_ui_delta
    clr.l -(%sp)
    clr.l -(%sp)
    move.l %d0,-(%sp)
    jsr ha_ui_edit_c
    lea 12(%sp),%sp
    tst.l %d0
    beq.s .ha_edit_done
    jsr hd_edit_finish
    jmp ch_ui_redraw
.ha_edit_done:
    rts
ha_step_push:
    move.l 8(%sp),%d0
    cmpi.l #1,%d0
    bne.s .ha_edit_done
    moveq #1,%d1
    moveq #0,%d0
    bra.s .ha_step_edit
ha_step_encoder:
    move.l 8(%sp),%d1
    moveq #4,%d0
    jsr mh_ui_delta
    moveq #0,%d1
.ha_step_edit:
    pea 1
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr ha_ui_edit_c
    lea 12(%sp),%sp
    tst.l %d0
    beq.s .ha_edit_done
    jsr hd_edit_finish
    jsr hd_bitmaps
    lea -80(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40050ec2
