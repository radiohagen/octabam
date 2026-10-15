    .include "remix.inc"
/* CHORD PLAY, mode 6. Stock dispatch reaches ch_play_key only in the
 * playing layout; grid recording retains its sequencer key layer.
 * Root keys retain pitch AND track until release. Variations are held
 * in a most-recent-first stack, independent of the encoder's base choice.
 */
    .text
    .global ch_play_key,ch_play_modes,ch_mode_names,ch_mode_icons
    .global ch_modifiers,ch_pressed,ch_octave_compare
ch_play_key:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.w .key_stock
    tst.l 0x80000012
    beq.w .key_stock
    lea -28(%sp),%sp
    movem.l %d2-%d7/%a2,(%sp)
    move.l 32(%sp),%d2 /* trig index */
    move.l 36(%sp),%d3 /* 1 down, 0 up; ignore repeats */
    cmpi.l #15,%d2
    bhi.w .key_done
    cmpi.l #1,%d3
    bhi.w .key_done
    moveq #0,%d4
    move.b 0x100b14cc,%d4
    cmpi.l #7,%d4
    bhi.w .key_done
    cmpi.l #8,%d2
    bcc.w .key_modifier
    lea ch_pressed,%a2
    lea (%a2,%d2.l*4),%a2
    move.l (%a2),%d5 /* -1 or track<<8 | pitch */
    tst.l %d3
    beq.w .key_release
    tst.l %d5
    bpl.w .key_done
    move.l %d4,%d0
    jsr mh_scale_record
    tst.l %d0
    bpl.s .key_scale
    moveq #0,%d0 /* KEY OFF: C-major root keyboard; each root builds its own major chord */
.key_scale:
    move.l %d0,%d1
    lsr.l #6,%d1
    lea ch_scale_masks,%a0
    moveq #0,%d6
    move.w (%a0,%d1.l*2),%d6
    lsr.l #2,%d0
    andi.l #15,%d0
    move.l %d0,%d7 /* tonic */
    move.l 0x400beba2,%d1
    moveq #12,%d0
    muls.l %d1,%d0
    add.l %d7,%d0
    move.l %d0,%d5
    move.l %d2,%d1
    beq.s .key_root_ready
.key_degree:
    addq.l #1,%d5
    move.l %d5,%d0
    sub.l %d7,%d0
.key_mod:
    cmpi.l #12,%d0
    blt.s .key_test
    subi.l #12,%d0
    bra.s .key_mod
.key_test:
    btst %d0,%d6
    beq.s .key_degree
    subq.l #1,%d1
    bne.s .key_degree
.key_root_ready:
    cmpi.l #127,%d5
    bhi.w .key_done
    move.l %d4,%d0
    lsl.l #8,%d0
    or.l %d5,%d0
    move.l %d0,(%a2)
    lea ch_last_root,%a0
    move.b %d5,(%a0,%d4.l)
    /* A new physical root resolves the currently held variation, or base.
     * A released variation stays sounding only until this new root edge. */
    move.l %d4,%d0
    lsl.l #3,%d0
    lea ch_modifiers,%a0
    moveq #0,%d1
    move.b (%a0,%d0.l),%d1
    cmpi.l #7,%d1
    bls.s .key_quality_store
    move.l %d4,%d0
    jsr ch_base_get
    move.l %d0,%d1
.key_quality_store:
    lea ch_live,%a0
    move.b %d1,(%a0,%d4.l)
.key_quality_ready:
    bsr.w .key_velocity
    bsr.w .key_send
    bra.w .key_done
.key_release:
    tst.l %d5
    bmi.w .key_done
    move.l %d5,%d4
    lsr.l #8,%d4
    andi.l #127,%d5
    moveq #-1,%d0
    move.l %d0,(%a2)
    moveq #0,%d6
    bsr.w .key_send
    bra.w .key_done
.key_modifier:
    subq.l #8,%d2
    lea ch_mod_owner,%a0
    tst.l %d3
    beq.s .modifier_owner_release
    move.b %d4,(%a0,%d2.l)
    bra.s .modifier_owner_ready
.modifier_owner_release:
    moveq #0,%d4
    move.b (%a0,%d2.l),%d4
    moveq #-1,%d0
    move.b %d0,(%a0,%d2.l)
    cmpi.l #7,%d4
    bhi.w .key_done
.modifier_owner_ready:
    /* Stack per track: 8 bytes, 0xff empty. Remove before prepend. */
    lea ch_modifiers,%a2
    move.l %d4,%d0
    lsl.l #3,%d0
    adda.l %d0,%a2
    moveq #0,%d5
    moveq #0,%d6
.modifier_remove:
    moveq #0,%d0
    move.b (%a2,%d5.l),%d0
    cmp.l %d2,%d0
    beq.s .modifier_skip
    move.b %d0,(%a2,%d6.l)
    addq.l #1,%d6
.modifier_skip:
    addq.l #1,%d5
    cmpi.l #8,%d5
    bne.s .modifier_remove
    moveq #-1,%d0
    move.b %d0,7(%a2)
    tst.l %d3
    beq.w .key_done /* Release updates held keys only; never retrigger. */
    moveq #7,%d5
.modifier_shift:
    move.b -1(%a2,%d5.l),%d0
    move.b %d0,(%a2,%d5.l)
    subq.l #1,%d5
    bne.s .modifier_shift
    move.b %d2,(%a2)
.modifier_selected:
    moveq #0,%d0
    move.b (%a2),%d0
    cmpi.l #7,%d0
    bls.s .modifier_apply
    move.l %d4,%d0
    jsr ch_base_get
.modifier_apply:
    lea ch_live,%a0
    cmp.b (%a0,%d4.l),%d0
    beq.w .key_done
    move.b %d0,(%a0,%d4.l)
    /* A quality change restarts each currently held root on this track. */
    lea ch_pressed,%a2
    moveq #0,%d7
.modifier_retrigger:
    move.l (%a2),%d5
    tst.l %d5
    bmi.w .modifier_next
    move.l %d5,%d0
    lsr.l #8,%d0
    cmp.l %d4,%d0
    bne.s .modifier_next
    andi.l #127,%d5
    bsr.s .key_velocity
    bsr.s .key_send
.modifier_next:
    addq.l #4,%a2
    addq.l #1,%d7
    cmpi.l #8,%d7
    bne.s .modifier_retrigger
.key_done:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.s .key_no_draw
    jsr ch_play_leds
    jsr ch_play_guide
.key_no_draw:
    movem.l (%sp),%d2-%d7/%a2
    lea 28(%sp),%sp
    moveq #1,%d0
    rts
.key_velocity:
    moveq #0,%d0
    move.b 0x100b14cf,%d0
    move.l #0x18b2,%d1
    mulu.l %d1,%d0
    move.l %d4,%d1
    lsl.l #5,%d1
    add.l %d1,%d0
    move.l 0x46c82456,%a0
    adda.l %d0,%a0
    adda.l #0x8f163,%a0
    moveq #0,%d6
    move.b (%a0),%d6
    rts
.key_send:
    tst.l %d6
    beq.s .key_send_captured
    /* Capture quality beside this physical key's owned notes. A new root
     * can reset ch_live while an older root still sounds its latched shape. */
    move.l %a2,%d0
    subi.l #ch_pressed,%d0
    lsr.l #2,%d0
    lea ch_live,%a0
    move.b (%a0,%d4.l),%d1
    lea ch_pressed_quality,%a0
    move.b %d1,(%a0,%d0.l)
.key_send_captured:
    pea 1
    move.l %d6,-(%sp)
    move.l %d5,-(%sp)
    move.l %d4,-(%sp)
    jsr mh_keyboard
    lea 16(%sp),%sp
    rts
.key_stock:
    move.l %d2,-(%sp)
    move.l 8(%sp),%a0
    jmp 0x400501de

/* FUNC+LEFT/RIGHT's two mode comparisons. Return Z for native CHROMATIC
 * or MIDI CHORD PLAY without changing the mode or the key-edge argument. */
ch_octave_compare:
    move.l %d1,-(%sp)
    move.l 0x460d16f0,%d1
    cmpi.l #1,%d1
    beq.s .octave_flags
    tst.l 0x80000012
    beq.s .octave_no
    cmpi.l #6,%d1
    bra.s .octave_flags
.octave_no:
    moveq #-1,%d1
.octave_flags:
    movem.l (%sp),%d1 /* MOVEM and LEA preserve the comparison flags. */
    lea 4(%sp),%sp
    rts

    .balign 4
ch_play_modes: .long 0,1,6,4
ch_mode_names:
    .long 0x400b5f4b,0x400b5366,0x400b5370,0x400b6cb9,0x400b5376,0x400b5381,ch_play_title
ch_mode_icons:
    .long 0x400beaaa,0x400beae6,0x400bea82,0x400bea96,0x400beabe,0x400bead2,0x400beae6
ch_play_title: .asciz "CHORD PLAY"
    .balign 4
    .global ch_last_root
ch_last_root: .space 8,255
ch_modifiers: .space 64,255
ch_mod_owner: .space 8,255
ch_pressed: .space 32,255
ch_scale_masks: .word 0xab5,0x6ad,0x5ab,0xad5,0x6b5,0x5ad,0x56b

/* Paired trig LEDs: one channel for roots, the other for variations;
 * both channels mark a held key. Stock owns all grid-recording LEDs.
 */
    .global ch_play_leds,ch_play_guide
ch_play_leds:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.w .led_stock
    tst.l 0x80000012
    beq.w .led_stock
    tst.l 0x460d1736
    bne.w .led_stock
    lea -12(%sp),%sp
    movem.l %d2-%d4,(%sp)
    moveq #0,%d2
.led_key:
    move.l %d2,%d3
    add.l %d3,%d3
    /* Use the native steady layer. Timed flashes expire while stopped. */
    move.l %d3,-(%sp)
    jsr 0x400131c8
    addq.l #4,%sp
    addq.l #1,%d3
    move.l %d3,-(%sp)
    jsr 0x400131c8
    addq.l #4,%sp
    cmpi.l #8,%d2
    bcc.s .led_variation
    subq.l #1,%d3
.led_variation:
    pea 15
    move.l %d3,-(%sp)
    jsr 0x400135b0
    addq.l #8,%sp
    move.l %d3,-(%sp)
    jsr 0x400131a0
    addq.l #4,%sp
    cmpi.l #8,%d2
    bcc.s .led_modifier_held
    lea ch_pressed,%a0
    tst.l (%a0,%d2.l*4)
    bmi.s .led_next
    bra.s .led_held
.led_modifier_held:
    move.l %d2,%d0
    subq.l #8,%d0
    lea ch_mod_owner,%a0
    move.b (%a0,%d0.l),%d0
    cmpi.b #255,%d0
    beq.s .led_next
.led_held:
    moveq #1,%d0
    eor.l %d0,%d3
    pea 15
    move.l %d3,-(%sp)
    jsr 0x400135b0
    addq.l #8,%sp
    move.l %d3,-(%sp)
    jsr 0x400131a0
    addq.l #4,%sp
.led_next:
    addq.l #1,%d2
    cmpi.l #16,%d2
    bne.w .led_key
    movem.l (%sp),%d2-%d4
    lea 12(%sp),%sp
    rts
.led_stock:
    lea -68(%sp),%sp
    movem.l %d2-%d6/%a2-%a5,(%sp)
    jmp 0x40043fe4

ch_play_guide:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.w .guide_stock
    tst.l 0x80000012
    beq.w .guide_stock
    /* The guide also describes sequenced chords while grid REC is active.
     * Stock still owns the grid key dispatch and ch_play_leds grid path. */
    tst.l 0x460d1aec
    bne.w .guide_done
    /* Keep the stock CHROMATIC octave box at its exact native position.
     * The stock inverted title bar holds pitches while sounding, otherwise
     * CHORD PLAY. The chord name replaces the keyboard beside the octave box. */
    clr.l -(%sp)
    pea 31
    pea 118
    pea 8
    pea 60
    pea 0x400bf10a
    jsr 0x40012254
    lea 24(%sp),%sp
    pea 8
    pea 60
    pea 0x400bf10a
    pea .guide_octave
    jsr 0x400128a8
    lea 16(%sp),%sp
    move.l 0x400beba2,%d0
    subq.l #1,%d0
    move.l %d0,-(%sp)
    pea 0x400b465d /* stock %d */
    pea 0x400b527d /* stock octave width template: -1 */
    clr.l -(%sp)
    pea 1
    pea 9
    pea 68
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40013904
    lea 36(%sp),%sp
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr ch_chord_name
    tst.b (%a0)
    beq.s .guide_idle
    jsr ch_draw_chord_name
    moveq #0,%d0
    moveq #4,%d1
    jsr ch_note_text
    jsr ch_draw_note_line
    bra.s .guide_notes_done
.guide_idle:
    lea ch_play_title,%a0
    moveq #25,%d0
    bsr.w .guide_text
.guide_notes_done:
    /* Preserve the companion-file diagnostic in place of the note line. */
    moveq #0,%d0
    move.b 0x80000002,%d0
    lea ch_lock_status,%a1
    move.b (%a1,%d0.l),%d0
    cmpi.b #2,%d0
    bcs.s .guide_flush
    lea .guide_bad,%a0
    beq.s .guide_diagnostic
    lea .guide_mismatch,%a0
    cmpi.b #3,%d0
    beq.s .guide_diagnostic
    lea .guide_save_error,%a0
.guide_diagnostic:
    move.l %a0,-(%sp)
    clr.l -(%sp)
    pea 31
    pea 118
    pea 25
    pea 60
    pea 0x400bf10a
    jsr 0x40012254
    lea 24(%sp),%sp
    move.l (%sp)+,%a0
    moveq #25,%d0
    bsr.s .guide_text
.guide_flush:
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    jsr ch_draw_settings
    /* Same inverse title strip as native CHROMATIC; invert after text. */
    pea -1
    pea 31
    pea 118
    pea 25
    pea 60
    pea 0x400bf10a
    jsr 0x40012254
    lea 24(%sp),%sp
    moveq #1,%d0
    move.l %d0,0x46c7c72c
.guide_done:
    rts
.guide_stock:
    lea -44(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40044928
.guide_text: /* a0 text, d0 baseline */
    move.l %a0,-(%sp)
    pea -1
    move.l %d0,-(%sp)
    pea 61
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    rts
    .balign 4
.guide_octave:
    /* Crop the native keyboard bitmap to its 17-column octave indicator.
     * Reference the user's stock graphics in place; no firmware bytes copied. */
    .long 17,16,1,0x400caf30,0x400cb01c
.guide_bad: .asciz "CHRD FILE BAD"
.guide_mismatch: .asciz "CHRD MISMATCH"
.guide_save_error: .asciz "CHRD SAVE ERR"

    .global ch_refresh_quality
/* d1 track; recompute held override/base and retrigger owned roots. */
ch_refresh_quality:
    lea -28(%sp),%sp
    movem.l %d2-%d7/%a2,(%sp)
    move.l %d1,%d4
    move.l %d1,%d0
    lsl.l #3,%d0
    lea ch_modifiers,%a2
    adda.l %d0,%a2
    bra.w .modifier_selected

/* Native playing-layout cleanup supplies the track as its only argument.
 * Release captured roots before native mode dispatch (which knows no mode 6).
 * No held variation survives a switch into grid or another playing mode.
 */
    .global ch_release_track
ch_release_track:
    lea -24(%sp),%sp
    movem.l %d2-%d6/%a2,(%sp)
    move.l 28(%sp),%d4
    lea ch_pressed,%a2
    moveq #8,%d2
.release_root:
    move.l (%a2),%d5
    bmi.s .release_next
    move.l %d5,%d0
    lsr.l #8,%d0
    cmp.l %d4,%d0
    bne.s .release_next
    moveq #-1,%d0
    move.l %d0,(%a2)
    andi.l #127,%d5
    moveq #0,%d6
    bsr.w .key_send
.release_next:
    addq.l #4,%a2
    subq.l #1,%d2
    bne.s .release_root
    cmpi.l #7,%d4
    bhi.s .release_done
    lea ch_modifiers,%a0
    move.l %d4,%d0
    lsl.l #3,%d0
    moveq #-1,%d1
    move.l %d1,(%a0,%d0.l)
    move.l %d1,4(%a0,%d0.l)
    lea ch_mod_owner,%a0
    moveq #8,%d0
.release_modifier:
    cmp.b (%a0),%d4
    bne.s .release_mod_next
    move.b %d1,(%a0)
.release_mod_next:
    addq.l #1,%a0
    subq.l #1,%d0
    bne.s .release_modifier
    move.l %d4,%d0
    jsr ch_base_get
    lea ch_live,%a0
    move.b %d0,(%a0,%d4.l)
.release_done:
    movem.l (%sp),%d2-%d6/%a2
    lea 24(%sp),%sp
    lea -16(%sp),%sp
    movem.l %d2-%d3/%a2-%a3,(%sp)
    jmp 0x40043730

/* REC entering grid bypasses stock playing-mode cleanup. Release our
 * owned notes before the grid layout takes over physical key releases. */
    .global ch_grid_toggle
ch_grid_toggle:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.s .grid_stock
    tst.l 0x80000012
    beq.s .grid_stock
    tst.l 0x460d1736
    bne.s .grid_stock
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr 0x400438dc
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
.grid_stock:
    lea 0x4007e998,%a0
    jmp 0x40048790

    .balign 4
    .global ch_pressed_quality
ch_pressed_quality: .space 8,0
