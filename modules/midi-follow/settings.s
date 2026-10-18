/* Follow settings in native Parts. UI getters read the selected Part;
 * _play uses the receiver track's engine context; _at takes explicit d1.
 * Getters preserve all registers except d0/condition codes. */
    .text
    .macro FIELD name,slot,shift,mask,maximum,default,bias
    .global bf_\name\()_get,bf_\name\()_play,bf_\name\()_at
bf_\name\()_get:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    bra.s .L\name\()_context
bf_\name\()_play:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_play_context
.L\name\()_context:
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w bf_\name\()_at
    move.l (%sp)+,%d1
    tst.l %d0
    rts
bf_\name\()_at:
    move.l %d2,-(%sp)
    moveq #\slot,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .L\name\()_default
    .if \shift
    lsr.l #\shift,%d0
    .endif
    andi.l #\mask,%d0
    cmpi.l #\maximum,%d0
    bls.s .L\name\()_bias
.L\name\()_default:
    moveq #\default,%d0
.L\name\()_bias:
    .if \bias
    subq.l #\bias,%d0
    .endif
    move.l (%sp)+,%d2
    tst.l %d0
    rts
    .endm
    FIELD source,3,0,255,8,-1,0
    FIELD mode,15,4,3,2,0,0
    FIELD response,12,1,1,1,0,0
    FIELD fixed,13,0,15,10,3,0
    FIELD offset,13,4,7,4,2,2
    FIELD home,15,0,15,10,3,0

/* UI write helpers. d0 track,d1 value. Preserve all except d0/CC.
 * Packed subfields preserve their neighbours, including Loopback DEST. */
    .macro STORE name,slot,mask,shift,maximum,bias,invalidate=0
    .global bf_\name\()_set
bf_\name\()_set:
    lea -24(%sp),%sp
    movem.l %d1-%d5/%a0,(%sp)
    move.l %d0,%d4
    move.l %d1,%d5
    .if \bias
    addq.l #\bias,%d5
    .endif
    cmpi.l #\maximum,%d5
    bhi.s .L\name\()_bad
    jsr mp_ui_context
    move.l %d0,%d1
    move.l %d4,%d0
    moveq #\slot,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .L\name\()_bad
    move.l %d0,%d3
    andi.l #\mask,%d0
    .if \shift
    lsl.l #\shift,%d5
    .endif
    or.l %d5,%d0
    cmp.l %d3,%d0
    beq.s .L\name\()_same
    move.l %d0,%d3
    move.l %d4,%d0
    jsr mp_write
    .if \invalidate
    tst.l %d0
    beq.s .L\name\()_done
    move.l %d0,-(%sp)
    move.l %d4,%d0
    jsr bf_register_edited
    move.l (%sp)+,%d0
    .endif
    bra.s .L\name\()_done
.L\name\()_same:
    moveq #1,%d0
    bra.s .L\name\()_done
.L\name\()_bad:
    moveq #0,%d0
.L\name\()_done:
    movem.l (%sp),%d1-%d5/%a0
    lea 24(%sp),%sp
    rts
    .endm
    STORE source,3,0,0,8,0,1
    STORE mode,15,15,4,2,0,1
    STORE response_value,12,125,1,1,0
    STORE fixed,13,112,0,10,0
    STORE offset,13,15,4,4,2
    STORE home,15,48,0,10,0,1

/* d0 track -> ultimate playback source; invalid/cyclic routes fall back to
 * the original receiver. Every hop uses that source track's own context. */
    .global bf_source_resolve,bf_source_resolve_at
bf_source_resolve:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_play_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w bf_source_resolve_at
    move.l (%sp)+,%d1
    tst.l %d0
    rts
bf_source_resolve_at:
    lea -12(%sp),%sp
    movem.l %d1-%d3,(%sp)
    move.l %d0,%d2
    moveq #8,%d3
    bsr.w bf_source_at
    tst.l %d0
    beq.s .resolve_bad
    subq.l #1,%d0
.resolve_next:
    cmpi.l #7,%d0
    bhi.s .resolve_bad
    move.l %d0,%d1
    bsr.w bf_source_play
    tst.l %d0
    beq.s .resolve_found
    subq.l #1,%d0
    cmp.l %d2,%d0
    beq.s .resolve_bad
    subq.l #1,%d3
    bne.s .resolve_next
.resolve_bad:
    move.l %d2,%d0
    bra.s .resolve_done
.resolve_found:
    move.l %d1,%d0
.resolve_done:
    movem.l (%sp),%d1-%d3
    lea 12(%sp),%sp
    rts
