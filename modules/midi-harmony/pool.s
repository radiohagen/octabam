/* Regenerate a sequence arp pool at the next native track iteration after
 * a mode change. That keeps an old transposed Harmony pool from receiving
 * stock TRAN a second time when switching OFF. Live held pools retain their
 * captured pitches and ownership. Native note-off processing remains intact.
 */
    .text
    .global hd_tick
hd_tick:
    lea -68(%sp),%sp
    movem.l %d0-%d7/%a0-%a6,(%sp)
    move.l %d7,-(%sp)
    jsr hd_event_tick_c
    addq.l #4,%sp
    lea hd_rebuild,%a0
    tst.b (%a0,%d7.l)
    beq.w .tick_done
    clr.b (%a0,%d7.l)
    /* A real trig rebuilds through mh_sequence later in this iteration. */
    moveq #1,%d0
    lsl.l %d7,%d0
    and.l -42(%fp),%d0
    bne.w .tick_done
    moveq #10,%d0
    mulu.l %d7,%d0
    lea 0x46c77b1e,%a0
    move.b (%a0,%d0.l),%d0
    cmpi.b #1,%d0
    beq.w .tick_done
    moveq #0,%d2
    move.b 0x220(%a5),%d2
    move.b %d2,60(%sp)
    moveq #0,%d1
    move.b 0x223(%a5),%d1
    add.l %d2,%d1
    subi.l #64,%d1
    move.b %d1,61(%sp)
    moveq #0,%d1
    move.b 0x224(%a5),%d1
    add.l %d2,%d1
    subi.l #64,%d1
    move.b %d1,62(%sp)
    moveq #0,%d1
    move.b 0x225(%a5),%d1
    add.l %d2,%d1
    subi.l #64,%d1
    move.b %d1,63(%sp)
    move.l %d7,%d0
    jsr ch_sequence_context
    move.l %d7,%d0
    lea 60(%sp),%a0
    jsr hd_sequence_prepare
    moveq #0,%d1
    move.b 0x22c(%a5),%d1
    subi.l #64,%d1
    lea 0x46c7a124,%a1
    moveq #0,%d2
    move.b (%a1,%d7.l),%d2
    add.l %d2,%d1
    jsr mh_generate
    lea mh_muted,%a1
    clr.b (%a1,%d7.l)
    tst.l %d0
    bpl.s .pool_valid
    moveq #1,%d2
    move.b %d2,(%a1,%d7.l)
.pool_valid:
    lea ch_sequence_root,%a1
    move.b 60(%sp),%d1
    move.b %d1,(%a1,%d7.l)
    tst.l %d0
    ble.s .pool_native
    move.l %d7,%d0
    jsr mh_voice
    moveq #0,%d0
    move.b 60(%sp),%d0
    cmpi.l #127,%d0
    bls.s .pool_native
    clr.l 60(%sp)
    lea mh_muted,%a1
    moveq #1,%d2
    move.b %d2,(%a1,%d7.l)
.pool_native:
    lea 60(%sp),%a0
    move.l %a0,-(%sp)
    move.l %d7,-(%sp)
    jsr 0x40099c08
    addq.l #8,%sp
.tick_done:
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 68(%sp),%sp
    move.l -36(%fp),%a0
    move.b (%a0),%d0
    extb.l %d0
    jmp 0x4009f9cc
