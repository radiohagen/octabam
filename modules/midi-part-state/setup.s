/* NOTE SETUP YES commits all six staged fields. Module settings are already
 * live in the selected Part; refresh only their staged slots before stock
 * copies them. Never replay a HARM conversion or disturb CHAN/BANK/PROG/SBNK.
 */
    .include "remix.inc"
    .text
    .global mp_note_confirm
mp_note_confirm:
    lea -16(%sp),%sp
    movem.l %d0-%d2/%a0,(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
.ifdef HAVE_FOLLOW
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    moveq #3,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .harmony
    move.l %d0,0x460d5cc0
.endif
.harmony:
.ifdef HAVE_HARMONY
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    moveq #5,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .stock
    move.l %d0,0x460d5cc8
.endif
.stock:
    movem.l (%sp),%d0-%d2/%a0
    lea 16(%sp),%sp
    lea -44(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x4004af28

/* Shared native event boundaries. Follow and Harmony must not compete for
 * these hooks; an absent consumer is compiled out, leaving stock replay. */
    .global mp_start_a,mp_start_b,mp_sent_a,mp_sent_b
mp_start_a:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c3da
mp_start_b:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c4da
.transport:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    .ifdef HAVE_FOLLOW
    jsr bf_register_reset
    .endif
    .ifdef HAVE_HARMONY
    jsr ha_transport_c
    .endif
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
mp_sent_a:
    bsr.s .sent
    move.b 0x400d807c,%d1
    extb.l %d1
    jmp 0x4009fbb8
mp_sent_b:
    bsr.s .sent
    move.b 0x400d807c,%d0
    extb.l %d0
    jmp 0x4009fd00
.sent:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    tst.b 0x400d807e
    beq.s .sent_done
    cmpi.l #7,%d7
    bhi.s .sent_done
    moveq #10,%d0
    mulu.l %d7,%d0
    lea 0x46c77b1e,%a0
    move.b (%a0,%d0.l),%d0
    cmpi.b #1,%d0
    beq.s .sent_done /* Live keyboard arp is not a sequenced event. */
    .ifdef HAVE_FOLLOW
    move.l %d7,%d0
    jsr bf_register_sent
    .endif
    .ifdef HAVE_HARMONY
    jsr ha_note_sent
    .endif
.sent_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
