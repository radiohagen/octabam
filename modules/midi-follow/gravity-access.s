    .text
    /* C calls the established register-ABI Part readers. */
    .macro READER name,target
    .global \name
\name:
    move.l 4(%sp),%d0
    jmp \target
    .endm
    READER bf_context_c,mp_play_context
    READER bf_epoch_c,mp_epoch
    READER bf_mode_c,bf_mode_play
    READER bf_home_c,bf_home_play
    READER bf_source_c,bf_source_play
    READER bf_resolve_c,bf_source_resolve

    .global bf_gravity
/* d0 pitch class,d1 receiver; preserve everything except d0/CC. */
bf_gravity:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr bf_gravity_c
    addq.l #8,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
    .macro EVENT name,target
    .global \name
\name:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr \target
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
    .endm
    EVENT bf_register_sync,bf_sync_c
    EVENT bf_register_begin,bf_begin_c
    EVENT bf_register_sent,bf_sent_c
    EVENT bf_register_reset,bf_reset_c

    .global bf_register_edited
/* UI edits invalidate only the receiver whose playing Part was edited. */
bf_register_edited:
    lea -20(%sp),%sp
    movem.l %d0-%d2/%a0-%a1,(%sp)
    jsr mp_play_context
    move.l %d0,%d2
    jsr mp_ui_context
    cmp.l %d2,%d0
    bne.s .edited_done
    move.l (%sp),-(%sp)
    jsr bf_forget_c
    addq.l #4,%sp
.edited_done:
    movem.l (%sp),%d0-%d2/%a0-%a1
    lea 20(%sp),%sp
    rts
