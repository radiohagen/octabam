/* Native MIDI SETUP flags (offset 12): Follow bits 0..1, DEST bits 2..3.
 * UI addresses the selected Part; routing follows each track's playing Part.
 * Runtime route bytes are only the applied cache. Invalid DEST falls back EXT.
 */
    .text
    .global lb_dest_get,lb_dest_at,lb_dest_set,lb_part_sync,lb_dest_write
lb_dest_get:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w lb_dest_at
    move.l (%sp)+,%d1
    rts
lb_dest_at:
    move.l %d2,-(%sp)
    moveq #12,%d2
    jsr mp_read
    cmpi.l #11,%d0
    bhi.s .dest_default
    lsr.l #2,%d0
    bra.s .dest_read_done
.dest_default:
    moveq #0,%d0
.dest_read_done:
    move.l (%sp)+,%d2
    rts
/* d0 track,d1 DEST -> accepted. Preserve all other registers. */
lb_dest_set:
    lea -24(%sp),%sp
    movem.l %d1-%d5/%a0,(%sp)
    move.l %d0,%d4
    move.l %d1,%d5
    cmpi.l #7,%d4
    bhi.s .dest_bad
    cmpi.l #2,%d5
    bhi.s .dest_bad
    jsr mp_ui_context
    move.l %d0,%d1
    move.l %d4,%d0
    moveq #12,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .dest_bad
    andi.l #3,%d0
    lsl.l #2,%d5
    or.l %d5,%d0
    move.l %d0,%d3
    move.l %d4,%d0
    jsr mp_write
    tst.l %d0
    beq.s .dest_done
    bsr.w lb_part_sync
    moveq #1,%d0
    bra.s .dest_done
.dest_bad:
    moveq #0,%d0
.dest_done:
    movem.l (%sp),%d1-%d5/%a0
    lea 24(%sp),%sp
    rts
/* C ABI for port/debug tooling; same persistent path as the panel. */
lb_dest_write:
    move.l 4(%sp),%d0
    move.l 8(%sp),%d1
    bra.w lb_dest_set
/* Preserve caller registers. A context replacement releases the old identity
 * even when its destination happens to be unchanged. mp_read observes the
 * shared coherent Part snapshot while native copy/clear is in progress.
 */
lb_part_sync:
    lea -44(%sp),%sp
    movem.l %d0-%d7/%a0-%a2,(%sp)
    moveq #0,%d4
.part_track:
    move.l %d4,%d0
    jsr mp_play_context
    move.l %d0,%d5
    jsr mp_epoch
    move.l %d0,%d6
    lea lb_contexts,%a1
    cmp.l (%a1,%d4.l*4),%d5
    bne.s .part_replaced
    lea lb_epochs,%a1
    cmp.l (%a1,%d4.l*4),%d6
    beq.s .part_route
.part_replaced:
    move.l %d4,-(%sp)
    jsr lb_flush
    addq.l #4,%sp
    lea lb_contexts,%a1
    move.l %d5,(%a1,%d4.l*4)
    lea lb_epochs,%a1
    move.l %d6,(%a1,%d4.l*4)
.part_route:
    move.l %d4,%d0
    move.l %d5,%d1
    bsr.w lb_dest_at
    move.l %d0,-(%sp)
    move.l %d4,-(%sp)
    jsr lb_set_route
    addq.l #8,%sp
    addq.l #1,%d4
    cmpi.l #8,%d4
    bne.s .part_track
    movem.l (%sp),%d0-%d7/%a0-%a2
    lea 44(%sp),%sp
    rts
    .balign 4
lb_contexts: .fill 8,4,-1
lb_epochs: .fill 8,4,-1
