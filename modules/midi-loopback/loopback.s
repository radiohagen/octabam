/* Per-track routing of complete MIDI channel messages.
 * lb_routes[8]: 0 EXT (default), 1 INT, 2 BOTH. Applied cache of native Part DEST settings.
 * Route before midi_send so INT reaches neither DIN nor USB's entry mirror.
 */
    .text
    .global lb_send, lb_receive, lb_capture, lb_next, lb_tick, lb_sync
    .global lb_routes, lb_set_route, lb_flush, lb_channels, lb_applied
    .global lb_head, lb_tail, lb_accepted, lb_delivered, lb_dropped, lb_highwater
    .global lb_owned, lb_internal_held, lb_ring, lb_current
    .global lb_wake, lb_wake_pending, lb_external_turn, lb_rx_internal
.set MIDI_Q, 0x46c7e974
.set POST, 0x40000c3c
.set RECEIVE, 0x40000d00
.set SEND, 0x40010bc8

/* A normal C-ABI sender reached only through selected stock call operands.
 * Preserve the producer's registers and original return PC. */
lb_send:
    lea %sp@(-40),%sp
    moveml %d0-%d6/%a0-%a2,%sp@
    movel %sp@(40),%d0
    movel %d7,%d1
    movel %sp@(44),%d2
    moveal %sp@(48),%a0
    bsr lb_capture
    tstl %d0
    beq.s .send_internal
    moveml %sp@,%d0-%d6/%a0-%a2
    lea %sp@(40),%sp
    jmp SEND
.send_internal:
    moveml %sp@,%d0-%d6/%a0-%a2
    lea %sp@(40),%sp
    rts

/* d0=source PC, d1=track, d2=len, a0=message. Returns d0 != 0 for external.
 * Ownership byte: high nibble track+1, bit0 internal, bit1 external.
 * A nonzero high nibble with no destination is a cleanup/drop tombstone:
 * swallow the stock pool's eventual old release, without releasing twice.
 * At most 128 internal held pitches across all channels reserve 128 releases.
 */
lb_capture:
    lea %sp@(-12),%sp
    moveml %d7/%a3-%a4,%sp@
    moveq #2,%d4
    cmpil #3,%d2
    bne.w .capture_done
    mvzb %a0@,%d2
    movel %d2,%d3
    andil #0xf0,%d3
    cmpil #lb_routed,%d0
    beq.w .routed_source
    cmpil #0x80,%d3
    beq.w .release_source
    cmpil #0x90,%d3
    beq.s .note_source
    cmpil #0xb0,%d3
    bne.w .capture_done
    cmpil #0x4009fef2,%d0
    beq.s .new_event
    cmpil #0x4009ffbe,%d0
    bne.w .capture_done
    bra.s .new_event
.note_source:
    tstb %a0@(2)
    beq.w .release_source
    cmpil #0x4009fbb2,%d0
    beq.s .new_event
    cmpil #0x4009fcfa,%d0
    bne.w .capture_done
.routed_source:
    cmpil #0x80,%d3
    beq.w .routed_release
    cmpil #0x90,%d3
    bne.s .routed_control
    tstb %a0@(2)
    beq.w .routed_release
    bra.s .new_event
.routed_control:
    cmpil #0xa0,%d3
    bcs.w .capture_done
    cmpil #0xe0,%d3
    bhi.w .capture_done
.new_event:
    cmpil #7,%d1
    bhi.w .capture_done
    movel %d1,%d7
    addql #1,%d7
    lsll #4,%d7
    cmpil #lb_routed,%d0
    bne.s .cached_route
    cmpil #2,%d5
    bhi.s .cached_route
    movel %d5,%d0
    bra.s .route_selected
.cached_route:
    lea lb_routes,%a1
    mvzb %a1@(0,%d1:l),%d0
.route_selected:
    cmpil #1,%d0
    bne.s .not_int
    moveq #1,%d4
    bra.s .admit
.not_int:
    cmpil #2,%d0
    bne.s .admit
    moveq #3,%d4
    bra.s .admit
.routed_release:
    /* An unowned release from an INT track must not escape externally.
     * Owned releases below still use their original destination bits. */
    movel %d5,%d0
    cmpil #2,%d0
    bls.s .release_route
    cmpil #7,%d1
    bhi.w .capture_done
    lea lb_routes,%a1
    mvzb %a1@(0,%d1:l),%d0
.release_route:
    cmpil #1,%d0
    bne.s .release
    moveq #0,%d4
    bra.s .release
.release_source:
    cmpil #0x4009f370,%d0
    beq.s .release
    cmpil #0x4009f8c2,%d0
    beq.s .release
    cmpil #0x4009fc54,%d0
    beq.s .release
    cmpil #0x4009fcd8,%d0
    beq.s .release
    cmpil #0x400a0074,%d0
    beq.s .release
    cmpil #0x400a00e6,%d0
    bne.w .capture_done
.release:
    moveq #-1,%d7
.admit:
    mvzb %a0@(1),%d3
    cmpil #127,%d3
    bhi.w .capture_done
    mvzb %a0@(2),%d1
    cmpil #127,%d1
    bhi.w .capture_done
    movel %d2,%d0
    andil #15,%d0
    lsll #7,%d0
    addl %d0,%d3
    lea lb_owned,%a1
    adda.l %d3,%a1
    movew %sr,%d6
    movew #0x2700,%sr
    tstl %d7
    bmi.w .owned_release
    movel %d2,%d0
    andil #0xf0,%d0
    cmpil #0x90,%d0
    bne.s .cc
    mvzb %a1@,%d0
    andil #3,%d0
    bne.w .duplicate
    btst #0,%d4
    beq.s .save_note
    movel lb_internal_held,%d0
    cmpil #128,%d0
    bcc.s .drop_note
    movel lb_head,%d5
    subl lb_tail,%d5
    andil #255,%d5
    cmpil #127,%d5
    bcc.s .drop_note
    addql #1,lb_internal_held
.save_note:
    movel %d7,%d0
    orl %d4,%d0
    moveb %d0,%a1@
    btst #0,%d4
    bne.s .append
    bra.w .unlock
.drop_note:
    bclr #0,%d4                 /* BOTH still sends externally */
    addql #1,lb_dropped
    bra.s .save_note
.cc:
    btst #0,%d4
    beq.w .unlock
    movel lb_head,%d5
    subl lb_tail,%d5
    andil #255,%d5
    cmpil #127,%d5
    bcs.s .append
    addql #1,lb_dropped
    bra.w .unlock
.duplicate:
    /* Stock coalesces same-channel/pitch sources before this point. Avoid
     * a second receiver held-count if a duplicate nevertheless reaches us. */
    andil #2,%d4
    bra.w .unlock
.owned_release:
    mvzb %a1@,%d0
    beq.w .unlock              /* unowned release keeps stock external path */
    movel %d0,%d4
    andil #3,%d4
    clrb %a1@
    btst #0,%d4
    beq.w .unlock
    subql #1,lb_internal_held
    movel lb_head,%d5
    subl lb_tail,%d5
    andil #255,%d5
.append:
    movel lb_head,%d0
    lea lb_ring,%a2
    lea %a2@(0,%d0:l:4),%a2
    moveb %d2,%a2@
    mvzb %a0@(1),%d3
    moveb %d3,%a2@(1)
    moveb %d1,%a2@(2)
    clrb %a2@(3)
    addql #1,%d0
    andil #255,%d0
    movel %d0,lb_head
    addql #1,lb_accepted
    addql #1,%d5
    cmpl lb_highwater,%d5
    bls.s .notify
    movel %d5,lb_highwater
.notify:
    tstb lb_wake_pending
    bne.s .unlock
    movel MIDI_Q+4,%d0
    cmpl MIDI_Q+16,%d0
    bhi.s .unlock
    moveq #1,%d0
    moveb %d0,lb_wake_pending
    pea lb_wake
    pea MIDI_Q
    jsr POST
    addql #8,%sp
.unlock:
    movew %d6,%sr
.capture_done:
    movel %d4,%d0
    andil #2,%d0
    moveml %sp@,%d7/%a3-%a4
    lea %sp@(12),%sp
    rts

/* C ABI lb_flush(track): release only that producer's owned destinations.
 * MIDI has no source identity on the receiver side; dedicate channels/pitches
 * to this module, as with a physical loopback. Leave tombstones until stock
 * retires its voice slots. Queued note-ons precede these releases. */
lb_flush:
    lea %sp@(-44),%sp
    moveml %d2-%d7/%a2-%a4,%sp@
    movel %sp@(48),%d7
    cmpil #7,%d7
    bhi.w .flush_done
    addql #1,%d7
    lsll #4,%d7
    movew %sr,%d2
    movew %d2,%sp@(40)
    movew #0x2700,%sr
    lea lb_owned,%a3
    subal %a4,%a4
.flush_loop:
    mvzb %a3@,%d0
    andil #0xf0,%d0
    cmpl %d7,%d0
    bne.s .flush_next
    movel %a4,%d0
    lsrl #7,%d0
    oril #0x80,%d0
    moveb %d0,%sp@(36)
    movel %a4,%d0
    andil #127,%d0
    moveb %d0,%sp@(37)
    clrb %sp@(38)
    lea %sp@(36),%a0
    movel #0x4009f370,%d0
    moveq #3,%d2
    bsr lb_capture
    tstl %d0
    beq.s .flush_mark
    pea %sp@(36)
    pea 3
    jsr SEND
    addql #8,%sp
.flush_mark:
    moveb %d7,%a3@
.flush_next:
    addql #1,%a3
    addql #1,%a4
    cmpal #2048,%a4
    bne.s .flush_loop
    movew %sp@(40),%d2
    movew %d2,%sr
.flush_done:
    moveml %sp@,%d2-%d7/%a2-%a4
    lea %sp@(44),%sp
    rts

/* C ABI lb_set_route(track, route). Invalid input has no effect. */
lb_set_route:
    lea %sp@(-16),%sp
    moveml %d2-%d4/%a2,%sp@
    movel %sp@(20),%d2
    movel %sp@(24),%d3
    cmpil #7,%d2
    bhi.s .route_done
    cmpil #2,%d3
    bhi.s .route_done
    movew %sr,%d4
    movew #0x2700,%sr
    lea lb_routes,%a2
    mvzb %a2@(0,%d2:l),%d0
    cmpl %d3,%d0
    beq.s .route_unlock
    movel %d2,%sp@-
    bsr lb_flush
    addql #4,%sp
    moveb %d3,%a2@(0,%d2:l)
    lea lb_applied,%a2
    moveb %d3,%a2@(0,%d2:l)
.route_unlock:
    movew %d4,%sr
.route_done:
    moveml %sp@,%d2-%d4/%a2
    lea %sp@(16),%sp
    rts

/* Sequencer boundary checks applied route edits and CHAN OFF.
 * Use the same effective channel bytes as the sequencer. */
lb_tick:
    jsr lb_part_sync
    lea %sp@(-40),%sp
    moveml %d0-%d6/%a0-%a2,%sp@
    bsr lb_sync
    moveml %sp@,%d0-%d6/%a0-%a2
    lea %sp@(40),%sp
    linkw %fp,#-104
    moveml %d2-%d7/%a2-%a5,%sp@
    jmp 0x4009f79c
lb_sync:
    lea %sp@(-24),%sp
    moveml %d2-%d4/%a2-%a4,%sp@
    movew %sr,%d4
    movew #0x2700,%sr
    moveq #0,%d2
    lea 0x46c76de0,%a4
.sync_loop:
    lea lb_routes,%a2
    mvzb %a2@(0,%d2:l),%d3
    lea lb_applied,%a3
    mvzb %a3@(0,%d2:l),%d0
    cmpl %d3,%d0
    bne.s .sync_flush
    lea lb_channels,%a2
    mvzb %a2@(0,%d2:l),%d0
    mvzb %a4@,%d1
    cmpl %d1,%d0
    beq.s .sync_next
.sync_flush:
    movel %d2,%sp@-
    bsr lb_flush
    addql #4,%sp
    moveb %d3,%a3@(0,%d2:l)
    lea lb_channels,%a2
    moveb %a4@,%d0
    moveb %d0,%a2@(0,%d2:l)
.sync_next:
    lea %a4@(68),%a4
    addql #1,%d2
    cmpil #8,%d2
    bne.s .sync_loop
    movew %d4,%sr
    moveml %sp@,%d2-%d4/%a2-%a4
    lea %sp@(24),%sp
    rts

/* Replace pea MIDI_Q / jsr a3, preserving the argument the stock task
 * removes after dispatch. lb_next runs only in the MIDI task. */
lb_receive:
    pea MIDI_Q
    bsr lb_next
    jmp 0x40005560

/* Return a complete message pointer in d0. Alternate native/internal
 * work when both queues are busy. Copy into a stable consumer slot before
 * releasing ring capacity; handlers finish before the next receive call.
 */
lb_next:
    lea %sp@(-16),%sp
    moveml %d2-%d3/%a2-%a3,%sp@
.next_again:
    movew %sr,%d3
    movew #0x2700,%sr
    movel lb_tail,%d0
    cmpl lb_head,%d0
    beq.s .native
    tstb lb_external_turn
    beq.s .internal
    tstl MIDI_Q+4
    bne.s .native
.internal:
    lea lb_ring,%a0
    movel %a0@(0,%d0:l:4),%d1
    movel %d1,lb_current
    addql #1,%d0
    andil #255,%d0
    movel %d0,lb_tail
    addql #1,lb_delivered
    moveq #1,%d0
    moveb %d0,lb_external_turn
    moveb %d0,lb_rx_internal
    movew %d3,%sr
    movel #lb_current,%d0
    bra.s .next_done
.native:
    movew %d3,%sr
    pea MIDI_Q
    jsr RECEIVE
    addql #4,%sp
    cmpil #lb_wake,%d0
    bne.s .native_done
    /* Wake token never reaches the MIDI parser/handler table. */
    clrb lb_wake_pending
    clrb lb_external_turn
    bra.s .next_again
.native_done:
    clrb lb_rx_internal
    clrb lb_external_turn
.next_done:
    moveml %sp@,%d2-%d3/%a2-%a3
    lea %sp@(16),%sp
    rts

    .balign 4
lb_routes: .space 8,0
lb_applied: .space 8,0
lb_channels: .space 8,0xff
lb_wake_pending: .byte 0
lb_external_turn: .byte 0
lb_rx_internal: .byte 0
    .balign 4
lb_head: .long 0
lb_tail: .long 0
lb_accepted: .long 0
lb_delivered: .long 0
lb_dropped: .long 0
lb_highwater: .long 0
lb_internal_held: .long 0
lb_current: .long 0
lb_wake: .long 0
lb_owned: .space 2048,0
lb_ring: .space 1024,0
