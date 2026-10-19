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
