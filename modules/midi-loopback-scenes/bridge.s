/* MIDI Scenes has its own sequencer CC loop and calls the stock control
 * emitter from its mixer. Keep those implementations unchanged. Qualify
 * their producers; every other sender continues through USB MIDI untouched.
 * The manifest pins scenes.s; the gate checks the private context offsets.
 */
    .text
    .global lb_scenes_send, lb_scenes_dest
lb_scenes_send:
    lea -60(%sp),%sp
    movem.l %d0-%d7/%a0-%a6,(%sp)
    move.l 60(%sp),%d0
    cmpi.l #scn_ccnote,%d0
    bcs.s .ordinary
    cmpi.l #scn_clear,%d0
    bcc.s .ordinary
    move.l 64(%sp),%d2
    cmpi.l #3,%d2
    bne.s .ordinary
    move.l 68(%sp),%a0
    moveq #0,%d0
    move.b (%a0),%d0
    andi.l #0xf0,%d0
    cmpi.l #0xb0,%d0
    bne.s .ordinary
    bsr.w lb_scenes_dest
    move.l 64(%sp),%d2
    move.l 68(%sp),%a0
    jsr lb_packet
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 60(%sp),%sp
    rts
.ordinary:
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 60(%sp),%sp
    jmp usbmidi_send_shim

/* d7 = source MIDI track; d6 = route. MIDI Scenes' actual mix context,
 * independent of the displayed Part or Loopback's last sequencer cache.
 * scn_pbi/scn_pp are at scn_state+288/+292 in the pinned source.
 */
lb_scenes_dest:
    moveq #0,%d6
    move.l scn_state+288,%d1
    cmpi.l #15,%d1
    bhi.s .done
    move.l scn_state+292,%d0
    cmpi.l #3,%d0
    bhi.s .done
    lsl.l #2,%d1
    add.l %d0,%d1
    move.l %d7,%d0
    jsr lb_dest_at
    move.l %d0,%d6
.done:
    rts
