/* Follow owns the MIDI transport and successful note-send boundaries. The
 * current MIDI Part State provides Part persistence, not event callbacks. */
    .text
    .include "remix.inc"
    .global bf_start_a,bf_start_b,bf_sent_a,bf_sent_b

bf_start_a:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c3da
bf_start_b:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c4da
.transport:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr bf_register_reset
    .ifdef HAVE_HARMONY
    jsr ha_transport_c
    .endif
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

bf_sent_a:
    bsr.s .sent
    move.b 0x400d807c,%d1
    extb.l %d1
    jmp 0x4009fbb8
bf_sent_b:
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
    move.l %d7,%d0
    jsr bf_register_sent
    .ifdef HAVE_HARMONY
    jsr ha_note_sent
    .endif
.sent_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
