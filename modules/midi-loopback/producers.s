/* Producer adapters. Never infer source track from an output channel.
 * C sender arguments are (length, bytes); preserve all producer registers.
 * Explicit route contexts: live keys use UI Part; bank/program uses the
 * bank/Part arguments of the stock setup sender; frame output uses cache.
 */
    .include "remix.inc"
    .text
    .global lb_track_send,lb_key_send,lb_setup_send,lb_control_send,lb_control_tail
    .global lb_packet,lb_routed
.macro SAVE
    lea -60(%sp),%sp
    movem.l %d0-%d7/%a0-%a6,(%sp)
.endm
.macro RESTORE
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 60(%sp),%sp
.endm
lb_track_send:
    SAVE
    moveq #-1,%d6
    bra.w .args
lb_key_send:
    SAVE
    move.l %d5,%d7
    jsr mp_ui_context
    bra.s .context
lb_setup_send:
    SAVE
    move.l %a3,%d7
    /* sender args 8 + return 4 + setup frame 44 + return 4 */
    move.l 120(%sp),%d0
    lsl.l #2,%d0
    add.l 124(%sp),%d0
.context:
    move.l %d0,%d1
    move.l %d7,%d0
    jsr lb_dest_at
    move.l %d0,%d6
.args:
    move.l 64(%sp),%d2
    move.l 68(%sp),%a0
    bsr.w lb_packet
    RESTORE
    rts

/* Cached live controls still have their source in d7. Ignore the generic
 * received-CC setter: its echoed traffic must not acquire an internal copy.
 * Preview is an original track event, just like turning the panel knob. */
lb_control_send:
    SAVE
    move.l 132(%sp),%d0
    bsr.s .control_route
    bra.s .args
.control_route:
    .ifdef HAVE_SCENES_BRIDGE
    cmpi.l #scn_morph,%d0
    bcs.s .native_control
    cmpi.l #scn_invalidate,%d0
    bcc.s .native_control
    jsr lb_scenes_dest
    rts
.native_control:
    .endif
    cmpi.l #0x4005542c,%d0
    beq.s .control_original
    cmpi.l #0x40043b0e,%d0
    beq.s .control_original
    moveq #0,%d6
    rts
.control_original:
    /* This producer reads the applied bank/Part, not the UI context. */
    moveq #0,%d1
    move.b 0x80000002,%d1
    lsl.l #2,%d1
    moveq #0,%d0
    move.b 0x80000003,%d0
    add.l %d0,%d1
    move.l %d7,%d0
    jsr lb_dest_at
    move.l %d0,%d6
    rts
/* All CC/PB/pressure tail branches converge before restoring d7. */
lb_control_tail:
    SAVE
    move.l 120(%sp),%d0
    bsr.s .control_route
    move.l 124(%sp),%d2
    move.l 128(%sp),%a0
    bsr.w lb_packet
    RESTORE
    jmp 0x4009f27c

/* d7 track, d6 route (-1 = applied), d2 length, a0 bytes.
 * Split the stock paired bank CC into complete packets. Two-byte packets
 * receive zero padding only in the internal queue, never on DIN or USB. */
lb_packet:
    lea -28(%sp),%sp
    movem.l %d2/%d6-%d7/%a3-%a5,(%sp)
    move.l %a0,%a3
    lea (%a0,%d2.l),%a4
    move.l %d6,%a5
.packet_next:
    cmpa.l %a4,%a3
    bcc.s .packet_done
    moveq #3,%d2
    moveq #0,%d0
    move.b (%a3),%d0
    andi.l #0xf0,%d0
    cmpi.l #0xc0,%d0
    beq.s .short_packet
    cmpi.l #0xd0,%d0
    bne.s .packet_copy
.short_packet:
    moveq #2,%d2
.packet_copy:
    lea (%a3,%d2.l),%a0
    cmpa.l %a4,%a0
    bhi.s .packet_done
    clr.l 24(%sp)
    move.b (%a3),24(%sp)
    move.b 1(%a3),25(%sp)
    cmpi.l #3,%d2
    bne.s .packet_capture
    move.b 2(%a3),26(%sp)
.packet_capture:
    move.l %d2,(%sp)
    move.l #lb_routed,%d0
    move.l %d7,%d1
    moveq #3,%d2
    move.l %a5,%d5
    lea 24(%sp),%a0
    jsr lb_capture
    tst.l %d0
    beq.s .packet_advance
    move.l %a3,-(%sp)
    move.l 4(%sp),-(%sp)
    jsr 0x40010bc8
    addq.l #8,%sp
.packet_advance:
    adda.l (%sp),%a3
    bra.s .packet_next
.packet_done:
    movem.l (%sp),%d2/%d6-%d7/%a3-%a5
    lea 28(%sp),%sp
    rts
/* Symbolic provenance accepted only by lb_capture's producer adapters. */
lb_routed:
    rts

/* STOP panic is per output channel, combining the routes of tracks actually
 * assigned to that channel. First release captured old destinations. */
    .global lb_panic
lb_panic:
    SAVE
    jsr lb_part_sync
    lea -20(%sp),%sp
    clr.l (%sp)
    clr.l 4(%sp)
    clr.l 8(%sp)
    clr.l 12(%sp)
    moveq #0,%d7
.panic_track:
    move.l %d7,-(%sp)
    jsr lb_flush
    addq.l #4,%sp
    move.l %d7,%d0
    moveq #68,%d1
    mulu.l %d1,%d0
    lea 0x46c76de0,%a0
    moveq #0,%d1
    move.b (%a0,%d0.l),%d1
    beq.s .panic_next
    subq.l #1,%d1
    andi.l #15,%d1
    lea lb_routes,%a0
    moveq #0,%d0
    move.b (%a0,%d7.l),%d0
    moveq #2,%d2
    tst.l %d0
    beq.s .panic_merge
    moveq #1,%d2
    cmpi.l #1,%d0
    beq.s .panic_merge
    moveq #3,%d2
.panic_merge:
    move.b (%sp,%d1.l),%d0
    or.l %d2,%d0
    move.b %d0,(%sp,%d1.l)
.panic_next:
    addq.l #1,%d7
    cmpi.l #8,%d7
    bne.s .panic_track
    moveq #0,%d7
.panic_channel:
    moveq #0,%d0
    move.b (%sp,%d7.l),%d0
    beq.s .panic_channel_next
    moveq #2,%d6
    cmpi.l #3,%d0
    beq.s .panic_emit
    moveq #1,%d6
    cmpi.l #1,%d0
    beq.s .panic_emit
    moveq #0,%d6
.panic_emit:
    move.l %d7,%d0
    ori.l #0xb0,%d0
    move.b %d0,16(%sp)
    move.b #123,17(%sp)
    clr.b 18(%sp)
    /* CC has no note ownership; use valid synthetic track zero. */
    move.l %d7,-(%sp)
    moveq #0,%d7
    lea 20(%sp),%a0
    moveq #3,%d2
    bsr.w lb_packet
    move.l (%sp)+,%d7
.panic_channel_next:
    addq.l #1,%d7
    cmpi.l #16,%d7
    bne.s .panic_channel
    lea 20(%sp),%sp
    RESTORE
    rts

/* The receiver's channel map contains audio bits 0..7, auto bit 8 and
 * MIDI-track forwarding bits 16..23. Internal packets target the audio/global
 * receive surface, never another MIDI-track transform/echo. Select a private
 * filtered view at the handler's map load; no shared stock state is changed.
 * This hook only runs inside receive handlers, so frame producers remain
 * routable even while the MIDI task is dispatching an internal message. */
    .global lb_rx_map
lb_rx_map:
    lea 0x46c7febe,%a0
    tst.b lb_rx_internal
    beq.s .rx_map_done
    lea -16(%sp),%sp
    movem.l %d0-%d2/%a1,(%sp)
    move.l #0x1ff,%d1
    tst.l 0x80000012
    beq.s .rx_map_audio
    move.l #0xff,%d1
.rx_map_audio:
    lea lb_rx_channels,%a1
    moveq #16,%d2
.rx_map_copy:
    move.l (%a0)+,%d0
    and.l %d1,%d0
    move.l %d0,(%a1)+
    subq.l #1,%d2
    bne.s .rx_map_copy
    lea lb_rx_channels,%a0
    /* A note with no internal listener must not enter native held bookkeeping.
     * The note-on handler otherwise records a held count before discovering
     * that it has no receiver, and its tokenless release cannot retire it. */
    move.l 16(%sp),%d0
    cmpi.l #0x4000e05e,%d0
    bne.s .rx_map_restore
    tst.l (%a0,%d4.l*4)
    bne.s .rx_map_restore
    move.l #0x4000e792,%d0
    move.l %d0,16(%sp)
.rx_map_restore:
    movem.l (%sp),%d0-%d2/%a1
    lea 16(%sp),%sp
.rx_map_done:
    rts
    .balign 4
lb_rx_channels: .space 64,0
