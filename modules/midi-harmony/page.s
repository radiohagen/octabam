/* Harmony window: native window/input-layer pattern from the Tuner module.
 * NOTE SETUP F press opens it; A=HARM, B=VOIC, C=SPRD, D=ROOT, E=SIZE.
 * Track is fixed while open. Track/page keys close the window; a subsequent
 * press selects the track/page. Transport and chromatic keys pass through.
 * Six-cell layout: top row HARM/VOIC/SPRD, ROOT/SIZE below HARM/VOIC; track in footer.
 * Values use the stock PLAYBACK 3/5/3/4/4-position selector widgets.
 * No UI-task/ISR hook: redraw only on open or an encoder edit.
 */
    .text
    .global mh_page_open,mh_page_close,mh_page_noop,mh_page_encoder
    .global mh_page_win,mh_page_track,mh_page_draw
mh_page_open:
    tst.l mh_page_win
    bne.w mh_page_close
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    cmpi.l #7,%d0
    bhi.s mh_page_noop
    move.l %d0,mh_page_track
    pea mh_page_close
    pea 5 /* stock modal class, shared with TEMPO/Tuner */
    clr.l -(%sp)
    clr.l -(%sp)
    pea 60
    pea 120
    jsr 0x4005829c
    lea 24(%sp),%sp
    move.l %d0,mh_page_win
    beq.s mh_page_noop
    move.l %d0,-(%sp)
    jsr 0x40056f4c
    addq.l #4,%sp
    pea mh_page_layer
    jsr 0x40031494
    addq.l #4,%sp
    bra.w mh_page_draw
mh_page_noop:
    rts
mh_page_close:
    tst.l mh_page_win
    beq.s mh_page_noop
    pea mh_page_win
    jsr 0x40055db4
    addq.l #4,%sp
    pea mh_page_layer
    jsr 0x4003146c
    addq.l #4,%sp
    jmp 0x40036548 /* redraw NOTE SETUP from current module values */

mh_page_encoder:
    lea -12(%sp),%sp
    movem.l %d2-%d4,(%sp)
    move.l 16(%sp),%d2 /* knob */
    move.l 20(%sp),%d3 /* signed detents */
    cmpi.l #4,%d2
    bhi.w .page_encoder_done
    move.l %d2,%d0
    move.l %d3,%d1
    jsr mh_ui_delta
    move.l %d0,%d3
    cmpi.l #4,%d2
    beq.w .page_size
    cmpi.l #3,%d2
    beq.w .page_omit
    move.l mh_page_track,%d4
    move.l %d4,%d0
    cmpi.l #2,%d2
    beq.s .page_sprd
    tst.l %d2
    bne.w .page_voic
    jsr mh_get
    /* Clamp delta before addition to prevent signed overflow. */
    cmpi.l #2,%d3
    ble.s .page_harm_low
    moveq #2,%d3
.page_harm_low:
    cmpi.l #-2,%d3
    bge.s .page_harm_add
    moveq #-2,%d3
.page_harm_add:
    add.l %d3,%d0
    bpl.s .page_harm_max
    moveq #0,%d0
.page_harm_max:
    cmpi.l #2,%d0
    ble.s .page_harm_set
    moveq #2,%d0
.page_harm_set:
    move.l %d0,%d1
    move.l %d4,%d0
    jsr mh_set
    bra.w .page_encoder_draw
.page_sprd:
    jsr mh_sprd_get
    cmpi.l #2,%d3
    ble.s .page_sprd_low
    moveq #2,%d3
.page_sprd_low:
    cmpi.l #-2,%d3
    bge.s .page_sprd_add
    moveq #-2,%d3
.page_sprd_add:
    add.l %d3,%d0
    bpl.s .page_sprd_max
    moveq #0,%d0
.page_sprd_max:
    cmpi.l #2,%d0
    ble.s .page_sprd_set
    moveq #2,%d0
.page_sprd_set:
    move.l %d0,%d1
    move.l %d4,%d0
    jsr mh_sprd_set
    bra.w .page_encoder_draw
.page_omit:
    move.l mh_page_track,%d4
    move.l %d4,%d0
    jsr mh_root_get
    cmpi.l #3,%d3
    ble.s .page_root_low
    moveq #3,%d3
.page_root_low:
    cmpi.l #-3,%d3
    bge.s .page_root_add
    moveq #-3,%d3
.page_root_add:
    add.l %d3,%d0
    bpl.s .page_root_max
    moveq #0,%d0
.page_root_max:
    cmpi.l #3,%d0
    ble.s .page_root_set
    moveq #3,%d0
.page_root_set:
    move.l %d0,%d1
    move.l %d4,%d0
    jsr mh_root_set
    bra.w .page_encoder_draw
.page_size:
    move.l mh_page_track,%d4
    move.l %d4,%d0
    jsr mh_size_get
    cmpi.l #3,%d3
    ble.s .page_size_low
    moveq #3,%d3
.page_size_low:
    cmpi.l #-3,%d3
    bge.s .page_size_add
    moveq #-3,%d3
.page_size_add:
    add.l %d3,%d0
    bpl.s .page_size_max
    moveq #0,%d0
.page_size_max:
    cmpi.l #3,%d0
    ble.s .page_size_set
    moveq #3,%d0
.page_size_set:
    move.l %d0,%d1
    move.l %d4,%d0
    jsr mh_size_set
    bra.w .page_encoder_draw
.page_voic:
    jsr mh_voic_get
    bsr.w .page_voic_index
    cmpi.l #4,%d3
    ble.s .page_voic_low
    moveq #4,%d3
.page_voic_low:
    cmpi.l #-4,%d3
    bge.s .page_voic_add
    moveq #-4,%d3
.page_voic_add:
    add.l %d3,%d0
    bpl.s .page_voic_max
    moveq #0,%d0
.page_voic_max:
    cmpi.l #4,%d0
    ble.s .page_voic_store
    moveq #4,%d0
.page_voic_store:
    /* UI ROOT/1ST/2ND/3RD/AUTO -> stable saved ROOT/AUTO/1ST/2ND/3RD. */
    move.l %d0,%d1
    beq.s .page_voic_set
    addq.l #1,%d1
    cmpi.l #5,%d1
    bne.w .page_voic_set
    moveq #1,%d1
.page_voic_set:
    move.l %d4,%d0
    jsr mh_voic_set
    bra.w .page_encoder_draw
.page_voic_index: /* Stored enum -> display order, d0 only. */
    tst.l %d0
    beq.s .page_voic_index_done
    cmpi.l #1,%d0
    bne.w .page_voic_index_manual
    moveq #4,%d0
    rts
.page_voic_index_manual:
    subq.l #1,%d0
.page_voic_index_done:
    rts
.page_encoder_draw:
    jsr mh_page_draw
.page_encoder_done:
    movem.l (%sp),%d2-%d4
    lea 12(%sp),%sp
    rts

mh_page_draw:
    lea -44(%sp),%sp
    movem.l %d2-%d3/%a2/%a5,(%sp)
    lea 16(%sp),%a2 /* 28-byte text scratch */
    move.l mh_page_win,%d0
    beq.w .page_draw_done
    move.l %d0,%a5
    lea 36(%a5),%a5
    move.l %a5,-(%sp)
    jsr 0x40035624
    addq.l #4,%sp
    /* Native PLAYBACK selectors: exact count, with our value formatters.
     * ABI: widget(x,y,slot,value,flags,formatter,surface).
     * Full layout, no lock highlight; the modal owns its own surface.
     */
    move.l mh_page_track,%d0
    jsr mh_get
    move.l %d0,%d1
    moveq #10,%d0
    lea mh_type_format,%a0
    lea 0x40046d9c,%a1 /* three positions */
    bsr.w .page_selector
    move.l mh_page_track,%d0
    jsr mh_voic_get
    bsr.w .page_voic_index
    move.l %d0,%d1
    moveq #49,%d0
    lea mh_page_voic_format,%a0
    lea 0x40046ab4,%a1 /* five positions */
    bsr.w .page_selector
    move.l mh_page_track,%d0
    jsr mh_sprd_get
    move.l %d0,%d1
    moveq #87,%d0
    lea mh_page_sprd_format,%a0
    lea 0x40046d9c,%a1 /* three positions */
    bsr.w .page_selector
    move.l mh_page_track,%d0
    jsr mh_root_get
    move.l %d0,%d1
    moveq #10,%d0
    lea mh_page_omit_format,%a0
    lea 0x40046c28,%a1 /* four-position ROOT widget */
    bsr.w .page_selector_bottom
    move.l mh_page_track,%d0
    jsr mh_size_get
    move.l %d0,%d1
    moveq #49,%d0
    lea mh_page_size_format,%a0
    lea 0x40046c28,%a1
    bsr.w .page_selector_bottom
    bsr.w .page_grid
    move.l mh_page_track,%d0
    addq.l #1,%d0
    move.l %d0,-(%sp)
    pea .page_title
    move.l %a2,-(%sp)
    jsr 0x40013a08
    lea 12(%sp),%sp
    moveq #4,%d0
    moveq #4,%d1
    move.l %a2,%a0
    bsr.w .page_text
    moveq #12,%d0
    moveq #52,%d1
    lea .page_harm_label,%a0
    bsr.w .page_text
    moveq #51,%d0
    moveq #52,%d1
    lea .page_voic_label,%a0
    bsr.w .page_text
    moveq #89,%d0
    moveq #52,%d1
    lea .page_sprd_label,%a0
    bsr.w .page_text
    moveq #12,%d0
    moveq #29,%d1
    lea .page_omit_label,%a0
    bsr.w .page_text
    moveq #51,%d0
    moveq #29,%d1
    lea .page_size_label,%a0
    bsr.w .page_text
    moveq #85,%d0
    moveq #4,%d1
    lea .page_back,%a0
    bsr.w .page_text
    moveq #1,%d0
    move.l %d0,0x46c7c72c
.page_draw_done:
    movem.l (%sp),%d2-%d3/%a2/%a5
    lea 44(%sp),%sp
    rts
.page_grid: /* Stock line/box primitive; six cells above a shared footer. */
    lea -8(%sp),%sp
    movem.l %d2/%a2,(%sp)
    moveq #4,%d2
    lea .page_grid_lines,%a2
.page_grid_line:
    pea 1
    move.l 12(%a2),-(%sp)
    move.l 8(%a2),-(%sp)
    move.l 4(%a2),-(%sp)
    move.l (%a2),-(%sp)
    move.l %a5,-(%sp)
    jsr 0x40012254
    lea 24(%sp),%sp
    lea 16(%a2),%a2
    subq.l #1,%d2
    bne.s .page_grid_line
    movem.l (%sp),%d2/%a2
    lea 8(%sp),%sp
    rts
.page_selector_bottom:
    moveq #13,%d2
    bra.s .page_selector_y
.page_selector: /* d0=x,d1=value,a0=formatter,a1=stock widget,a5=surface */
    moveq #36,%d2
.page_selector_y:
    move.l %a5,-(%sp)
    move.l %a0,-(%sp)
    clr.l -(%sp) /* flags: full widget, no highlight */
    move.l %d1,-(%sp)
    clr.l -(%sp) /* slot is unused by these stock widgets */
    move.l %d2,-(%sp)
    move.l %d0,-(%sp)
    jsr (%a1)
    lea 28(%sp),%sp
    rts
    .global mh_page_voic_format,mh_page_sprd_format,mh_page_size_format
mh_page_size_format:
    lea .page_sizes,%a1
    moveq #3,%d1
    bra.s .page_value_format
mh_page_omit_format:
    lea .page_omits,%a1
    moveq #3,%d1
    bra.s .page_value_format
mh_page_voic_format:
    lea .page_voices,%a1
    moveq #4,%d1
    bra.s .page_value_format
mh_page_sprd_format:
    lea .page_spreads,%a1
    moveq #2,%d1
.page_value_format: /* Native formatter ABI: (char *buffer, int value). */
    move.l 4(%sp),%a0
    move.l 8(%sp),%d0
    cmp.l %d1,%d0
    bls.s .page_value_valid
    moveq #0,%d0
.page_value_valid:
    move.l (%a1,%d0.l*4),%a1
.page_value_copy:
    move.b (%a1)+,(%a0)+
    bne.s .page_value_copy
    rts
.page_text: /* d0=x,d1=y,a0=string,a5=surface; native C ABI */
    move.l %a0,-(%sp)
    pea -1
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    move.l %a5,-(%sp)
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    rts
.page_title: .asciz "HARMONY T%d"
.page_harm_label: .asciz "HARM"
.page_voic_label: .asciz "VOIC"
.page_sprd_label: .asciz "SPRD"
.page_omit_label: .asciz "ROOT"
.page_size_label: .asciz "SIZE"
.page_nat: .asciz "NAT"
.page_two: .asciz "2"
.page_three: .asciz "3"
.page_four: .asciz "4"
.page_keep: .asciz "KEEP"
.page_omit_value: .asciz "OMIT"
.page_down1: .asciz "-1 OCT"
.page_down2: .asciz "-2 OCT"
.page_close: .asciz "CLOSE"
.page_open: .asciz "OPEN"
.page_wide: .asciz "WIDE"
.page_root: .asciz "ROOT"
.page_auto: .asciz "AUTO"
.page_first: .asciz "1ST"
.page_second: .asciz "2ND"
.page_third: .asciz "3RD"
.page_back: .asciz "NO:BACK"
    .balign 4
.page_grid_lines:
    .long 38,12,38,58
    .long 77,12,77,58
    .long 0,35,115,35
    .long 0,12,115,12
.page_omits: .long .page_keep,.page_omit_value,.page_down1,.page_down2
.page_voices: .long .page_root,.page_first,.page_second,.page_third,.page_auto
.page_spreads: .long .page_close,.page_open,.page_wide
.page_sizes: .long .page_nat,.page_two,.page_three,.page_four
mh_page_layer:
    .long 0,mh_page_keys,mh_page_encs,0,0,-1,-1
mh_page_keys:
    /* The opening F key's release is consumed; only a new press closes. */
    .irp key,0x31,0x32,0x3d,0x22,0x23,0x24,0x25,0x26,0x35,0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17
    .byte \key,0
    .long mh_page_close,0,0,0,0
    .word 0,0
    .endr
    /* Held knob pushes must not commit stock NOTE SETUP values. */
    .irp key,0x38,0x39,0x3a,0x3b,0x3c
    .byte \key,0
    .long 0,0,0,0,0
    .word 0,0
    .endr
    .byte 0xff,0
    .long 0,0,0,0,0
    .word 0,0
mh_page_encs:
    .irp knob,0,1,2,3,4,5,6
    .byte \knob,0
    .long mh_page_encoder,0,0,0,0
    .endr
    .byte 0xff,0
    .long 0,0,0,0,0
    .balign 4
mh_page_win: .long 0
mh_page_track: .long 0
