/* Harmony transport and successful-send boundaries when used alone.
 * HARMONY FOLLOW selects Follow's dispatcher for a combined image. */
    .text
    .global mh_start_a,mh_start_b,mh_sent_a,mh_sent_b

mh_start_a:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c3da
mh_start_b:
    bsr.s .transport
    move.l %d0,0x800065b8
    jmp 0x4009c4da
.transport:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr ha_transport_c
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

mh_sent_a:
    bsr.s .sent
    move.b 0x400d807c,%d1
    extb.l %d1
    jmp 0x4009fbb8
mh_sent_b:
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
    jsr ha_note_sent
.sent_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
