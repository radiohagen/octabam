/* RFOL D press: RFOL, MODE, OCT and UPDT. Native modal/input layer.
 * Transport/chromatic keys pass through; UPDT arms at the next ordinary trig. */
    .text
    .global bf_page_open,bf_page_close,bf_page_noop,bf_page_encoder
    .global bf_page_win,bf_page_track,bf_page_draw
bf_page_open:
    tst.l bf_page_win
    bne.w bf_page_close
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    cmpi.l #7,%d0
    bhi.s bf_page_noop
    move.l %d0,bf_page_track
    pea bf_page_close
    pea 5 /* stock modal class, shared with TEMPO/Tuner */
    clr.l -(%sp)
    clr.l -(%sp)
    pea 60
    pea 120
    jsr 0x4005829c
    lea 24(%sp),%sp
    move.l %d0,bf_page_win
    beq.s bf_page_noop
    move.l %d0,-(%sp)
    jsr 0x40056f4c
    addq.l #4,%sp
    pea bf_page_layer
    jsr 0x40031494
    addq.l #4,%sp
    bra.w bf_page_draw
bf_page_noop:
    rts
bf_page_close:
    tst.l bf_page_win
    beq.s bf_page_noop
    pea bf_page_win
    jsr 0x40055db4
    addq.l #4,%sp
    pea bf_page_layer
    jsr 0x4003146c
    addq.l #4,%sp
    jmp 0x40036548 /* refresh RFOL on the underlying NOTE SETUP */

bf_page_encoder:
    lea -12(%sp),%sp
    movem.l %d2-%d4,(%sp)
    move.l 16(%sp),%d4
    cmpi.l #3,%d4
    bhi.s .encoder_done
    move.l %d4,%d0
    move.l 20(%sp),%d1
    jsr bf_ui_delta
    move.l %d0,%d2
    move.l bf_page_track,%d0
    cmpi.l #3,%d4
    beq.s .encoder_response
    tst.l %d4
    beq.s .encoder_source
    move.l %d4,%d1
    subq.l #1,%d1
    jsr bf_reg_change
    bra.s .encoder_draw
.encoder_response:
    move.l %d0,%d3
    jsr bf_response_get
    add.l %d2,%d0
    bpl.s .response_high
    moveq #0,%d0
.response_high:
    cmpi.l #1,%d0
    ble.s .response_store
    moveq #1,%d0
.response_store:
    move.l %d0,%d1
    move.l %d3,%d0
    jsr bf_response_set
    bra.s .encoder_draw
.encoder_source:
    move.l %d2,%d1
    jsr bf_select
.encoder_draw:
    jsr bf_page_draw
.encoder_done:
    movem.l (%sp),%d2-%d4
    lea 12(%sp),%sp
    rts

bf_page_draw:
    lea -44(%sp),%sp
    movem.l %d2-%d3/%a2/%a5,(%sp)
    lea 16(%sp),%a2
    move.l bf_page_win,%d0
    beq.w .page_done
    move.l %d0,%a5
    lea 36(%a5),%a5
    move.l %a5,-(%sp)
    jsr 0x40035624
    addq.l #4,%sp
    move.l bf_page_track,%d0
    jsr bf_mode_get
    move.l %d0,%d1
    moveq #49,%d0
    lea bf_mode_format,%a0
    lea 0x40046f10,%a1 /* native two-position selector */
    bsr.w .page_selector
    move.l bf_page_track,%d0
    jsr bf_oct_get
    addq.l #2,%d0 /* Stock field hides negative values; format index back to OCT. */
    move.l %d0,%d1
    moveq #87,%d0
    lea bf_oct_format,%a0
    lea 0x400467a4,%a1 /* same stock field and value baseline as RFOL */
    bsr.w .page_selector
    move.l bf_page_track,%d0
    jsr bf_source_get
    move.l %d0,%d1
    moveq #10,%d0
    lea bf_format,%a0
    lea 0x400467a4,%a1 /* stock numeric/text field, like NOTE SETUP RFOL */
    bsr.w .page_selector
    move.l bf_page_track,%d0
    jsr bf_response_get
    move.l %d0,%d1
    moveq #10,%d0
    lea bf_response_format,%a0
    lea 0x40046f10,%a1 /* native two-position switch, like MODE */
    bsr.w .page_selector_bottom
    bsr.w .page_grid
    moveq #12,%d0
    moveq #29,%d1
    lea .response_label,%a0
    bsr.w .page_text
    moveq #51,%d0
    moveq #52,%d1
    lea .mode_label,%a0
    bsr.w .page_text
    moveq #52,%d1
    lea .oct_label,%a0
    bsr.w .page_oct_center
    moveq #12,%d0
    moveq #52,%d1
    lea .source_label,%a0
    bsr.w .page_text
    moveq #85,%d0
    moveq #4,%d1
    lea .back,%a0
    bsr.w .page_text
    moveq #1,%d0
    move.l %d0,0x46c7c72c
.page_done:
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
bf_oct_format: /* Stock formatter ABI: destination, octave + 2. */
    move.l 4(%sp),%a0
    move.l 8(%sp),%d0
    subq.l #2,%d0
    move.l %d0,-(%sp)
    pea .number
    move.l %a0,-(%sp)
    jsr 0x40013a08
    lea 12(%sp),%sp
    rts
bf_response_format:
    move.l 4(%sp),%a0
    lea .trig,%a1
    tst.l 8(%sp)
    beq.s .mode_copy
    lea .live,%a1
    bra.s .mode_copy
bf_mode_format:
    move.l 4(%sp),%a0
    lea .fixed,%a1
    tst.l 8(%sp)
    beq.s .mode_copy
    lea .source,%a1
.mode_copy:
    move.b (%a1)+,(%a0)+
    bne.s .mode_copy
    rts
.page_oct_center: /* Center OCT label in cell bounded by x=77 and x=115. */
    lea -8(%sp),%sp
    movem.l %d2/%a2,(%sp)
    move.l %d1,%d2
    move.l %a0,%a2
    move.l %a0,-(%sp)
    pea -1
    pea 0x400ba876
    jsr 0x40012f30
    lea 12(%sp),%sp
    lsr.l #1,%d0
    moveq #96,%d1
    sub.l %d0,%d1
    move.l %d1,%d0
    move.l %d2,%d1
    move.l %a2,%a0
    bsr.s .page_text
    movem.l (%sp),%d2/%a2
    lea 8(%sp),%sp
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
.response_label: .asciz "UPDT"
.trig: .asciz "TRIG"
.live: .asciz "LIVE"
.source_label: .asciz "RFOL"
.mode_label: .asciz "MODE"
.oct_label: .asciz "OCT"
.fixed: .asciz "FIXED"
.source: .asciz "SOURCE"
.number: .asciz "%d"
.back: .asciz "NO:BACK"
    .balign 4
.page_grid_lines:
    .long 38,12,38,58
    .long 77,12,77,58
    .long 0,35,115,35
    .long 0,12,115,12
bf_page_layer:
    .long 0,bf_page_keys,bf_page_encs,0,0,-1,-1
bf_page_keys:
    /* The opening D key's release is consumed; only a new press closes. */
    .irp key,0x31,0x32,0x3b,0x22,0x23,0x24,0x25,0x26,0x35,0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17
    .byte \key,0
    .long bf_page_close,0,0,0,0
    .word 0,0
    .endr
    /* Held knob pushes must not commit stock NOTE SETUP values. */
    .irp key,0x38,0x39,0x3a,0x3c,0x3d
    .byte \key,0
    .long 0,0,0,0,0
    .word 0,0
    .endr
    .byte 0xff,0
    .long 0,0,0,0,0
    .word 0,0
bf_page_encs:
    .irp knob,0,1,2,3,4,5,6
    .byte \knob,0
    .long bf_page_encoder,0,0,0,0
    .endr
    .byte 0xff,0
    .long 0,0,0,0,0
    .balign 4
bf_page_win: .long 0
bf_page_track: .long 0
