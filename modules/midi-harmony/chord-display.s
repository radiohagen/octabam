    .include "remix.inc"
/* UI-only snapshot of sounding notes. Native sequence ownership expires on
 * note-off/STOP; held live roots use Harmony's captured final pitches. Never
 * regenerate a voicing from UI code (AUTO would advance its history).
 */
    .text
    .global ch_display_snapshot,ch_display_root,ch_display_quality
    .global ch_display_notes,ch_sequence_root,ch_note_text
ch_display_snapshot: /* d0 track, preserves all registers */
    lea -32(%sp),%sp
    movem.l %d0-%d5/%a0-%a1,(%sp)
    move.l %d0,%d5
    moveq #-1,%d0
    move.b %d0,ch_display_root
    move.l %d0,ch_display_notes
    cmpi.l #7,%d5
    bhi.w .snapshot_done
    /* Prefer the latest held live root; releasing it reveals another held
     * root, or the sequencer. A remembered root alone is never sufficient. */
    lea ch_last_root,%a0
    moveq #0,%d4
    move.b (%a0,%d5.l),%d4
    moveq #-1,%d3
    lea ch_pressed,%a0
    moveq #8,%d2
.snapshot_key:
    move.l (%a0)+,%d0
    bmi.s .snapshot_next_key
    move.l %d0,%d1
    lsr.l #8,%d1
    cmp.l %d5,%d1
    bne.s .snapshot_next_key
    andi.l #127,%d0
    move.l %d0,%d3
    move.l %a0,%d1
    subi.l #ch_pressed+4,%d1
    lsr.l #2,%d1
    lea ch_pressed_quality,%a1
    move.b (%a1,%d1.l),%d1
    move.b %d1,ch_display_quality
    cmp.l %d4,%d0
    beq.s .snapshot_live
.snapshot_next_key:
    subq.l #1,%d2
    bne.s .snapshot_key
    tst.l %d3
    bmi.s .snapshot_sequence
.snapshot_live:
    move.l %d5,%d0
    lsl.l #7,%d0
    add.l %d3,%d0
    lea mh_held,%a0
    move.l (%a0,%d0.l*4),%d0
    cmpi.l #0xfeffffff,%d0
    beq.s .snapshot_bypass
    move.l %d0,ch_display_notes
    bra.s .snapshot_live_root
.snapshot_bypass:
    move.b %d3,ch_display_notes
.snapshot_live_root:
    move.l %d3,%d0
    move.l %d5,%d1
    jsr mh_quant
    move.b %d0,ch_display_root
    bra.s .snapshot_validate
.snapshot_sequence:
    move.l %d5,%d0
    lsl.l #5,%d0
    lea 0x46c77a1a,%a0 /* four {status,note} pairs; note=-1 when off */
    adda.l %d0,%a0
    lea ch_display_notes,%a1
    moveq #4,%d2
.snapshot_voice:
    move.l (%a0),%d0
    cmpi.l #127,%d0
    bhi.s .snapshot_voice_next
    move.b %d0,(%a1)
.snapshot_voice_next:
    addq.l #8,%a0
    addq.l #1,%a1
    subq.l #1,%d2
    bne.s .snapshot_voice
    lea ch_sequence_root,%a0
    move.b (%a0,%d5.l),%d0
    move.b %d0,ch_display_root
    lea ch_sequence_quality,%a0
    move.b (%a0,%d5.l),%d0
    move.b %d0,ch_display_quality
.snapshot_validate:
    lea ch_display_notes,%a0
    moveq #4,%d2
.snapshot_valid_voice:
    moveq #0,%d0
    move.b (%a0)+,%d0
    cmpi.l #127,%d0
    bls.s .snapshot_done
    subq.l #1,%d2
    bne.s .snapshot_valid_voice
    moveq #-1,%d0
    move.b %d0,ch_display_root
.snapshot_done:
    movem.l (%sp),%d0-%d5/%a0-%a1
    lea 32(%sp),%sp
    rts

/* d0 first voice, d1 exclusive end -> a0 text. Two voices fit even at C#-1.
 * MIDI 60 = C4, matching native CHROMATIC PLAY's octave indication.
 */
ch_note_text:
    lea -24(%sp),%sp
    movem.l %d2-%d5/%a2-%a3,(%sp)
    move.l %d0,%d4
    move.l %d1,%d5
    lea ch_display_notes,%a3
    lea ch_notes_text,%a2
    clr.b (%a2)
.notes_voice:
    moveq #0,%d2
    move.b (%a3,%d4.l),%d2
    cmpi.l #127,%d2
    bhi.w .notes_next
    cmpa.l #ch_notes_text,%a2
    beq.s .notes_pitch
    move.b #45,(%a2)+
.notes_pitch:
    moveq #-1,%d3
.notes_octave:
    addq.l #1,%d3
    subi.l #12,%d2
    bpl.s .notes_octave
    addi.l #12,%d2
    subq.l #1,%d3
    lea .notes_names,%a0
    move.l (%a0,%d2.l*4),%a0
.notes_copy:
    move.b (%a0)+,%d0
    beq.s .notes_number
    move.b %d0,(%a2)+
    bra.s .notes_copy
.notes_number:
    tst.l %d3
    bpl.s .notes_digit
    move.b #45,(%a2)+
    neg.l %d3
.notes_digit:
    addi.l #48,%d3
    move.b %d3,(%a2)+
.notes_next:
    addq.l #1,%d4
    cmp.l %d5,%d4
    bcs.w .notes_voice
    clr.b (%a2)
    lea ch_notes_text,%a0
    movem.l (%sp),%d2-%d5/%a2-%a3
    lea 24(%sp),%sp
    rts
    .balign 4
.notes_names: .long .nc,.ncs,.nd,.nds,.ne,.nf,.nfs,.ng,.ngs,.na,.nas,.nb
.nc: .asciz "C"
.ncs: .asciz "C#"
.nd: .asciz "D"
.nds: .asciz "D#"
.ne: .asciz "E"
.nf: .asciz "F"
.nfs: .asciz "F#"
.ng: .asciz "G"
.ngs: .asciz "G#"
.na: .asciz "A"
.nas: .asciz "A#"
.nb: .asciz "B"
    .balign 4
ch_sequence_root: .space 8,255
ch_display_root: .byte 255
ch_display_quality: .byte 0
    .balign 4
ch_display_notes: .long -1
ch_notes_text: .space 32

/* UI task only, immediately after its queue receive. Adjacent to, but not
 * overlapping, TUNER's loop-head detour. No ISR work or kernel messages.
 * Preserve the received message and every loop constant across the poll. */
    .global ch_display_tick
ch_display_tick:
    lea -60(%sp),%sp
    movem.l %d0-%d7/%a0-%a6,(%sp)
    jsr hd_ui_observe_c
    jsr hd_nv_poll_c
    bsr.w ch_display_poll
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 60(%sp),%sp
    move.l %d0,%a0
    addq.l #4,%sp
    move.b (%a0),%d0
    extb.l %d0
    jmp 0x40056c82
ch_display_poll:
    move.l 0x460d16f0,%d0
    cmpi.l #6,%d0
    bne.w .poll_inactive
    tst.l 0x80000012
    beq.w .poll_inactive
    /* Grid REC keeps the sounding-chord guide; only key dispatch changes. */
    tst.l 0x460d1aec
    bne.w .poll_inactive
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    bsr.w ch_display_snapshot
    cmp.l ch_draw_track,%d0
    bne.s .poll_changed
    move.l ch_display_notes,%d1
    cmp.l ch_draw_notes,%d1
    bne.s .poll_changed
    move.w ch_display_root,%d1
    cmp.w ch_draw_identity,%d1
    bne.s .poll_changed
    move.l 0x400beba2,%d1
    cmp.l ch_draw_octave,%d1
    bne.s .poll_changed
    bsr.w ch_settings_token
    cmp.l ch_draw_settings_token,%d1
    beq.s .poll_done
.poll_changed:
    move.l %d0,ch_draw_track
    move.l ch_display_notes,%d1
    move.l %d1,ch_draw_notes
    move.w ch_display_root,%d1
    move.w %d1,ch_draw_identity
    move.l 0x400beba2,%d1
    move.l %d1,ch_draw_octave
    bsr.w ch_settings_token
    move.l %d1,ch_draw_settings_token
    jsr ch_play_guide
.poll_done:
    rts
.poll_inactive:
    moveq #-1,%d0
    move.l %d0,ch_draw_track
    rts
    .balign 4
ch_draw_track: .long -1
ch_draw_notes: .long -1
ch_draw_octave: .long -1
ch_draw_settings_token: .long -1
ch_draw_identity: .word -1

/* Full-width single-line pitches. Use the native font normally. Long lists
 * retain native letters/digits, with a three-column sharp and narrow dashes.
 * A negative-octave sign needs no trailing gap before its digit. Even four
 * sharp notes in octave -1 fit in 57 pixels; never omit a voice or octave. */
    .global ch_draw_note_line
ch_draw_note_line: /* a0 text */
    lea -12(%sp),%sp
    movem.l %d2/%a2-%a3,(%sp)
    move.l %a0,%a2
    move.l %a0,-(%sp)
    pea -1
    pea 0x400ba876
    jsr 0x40012f30
    lea 12(%sp),%sp
    cmpi.l #58,%d0
    bhi.s .line_compact
    move.l %a2,-(%sp)
    pea -1
    pea 25
    pea 61
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    bra.w .line_done
.line_compact:
    moveq #61,%d2
.line_character:
    moveq #0,%d0
    move.b (%a2),%d0
    beq.w .line_done
    cmpi.b #35,%d0
    beq.s .line_sharp
    cmpi.b #45,%d0
    beq.s .line_dash
    move.l %a2,-(%sp)
    pea 1
    pea 25
    move.l %d2,-(%sp)
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    addq.l #4,%d2
    bra.s .line_next
.line_sharp:
    lea .line_sharp_bitmap,%a3
    moveq #25,%d0
    bsr.s .line_bitmap
    addq.l #4,%d2
    bra.s .line_next
.line_dash:
    lea .line_dash_bitmap,%a3
    moveq #27,%d0
    bsr.s .line_bitmap
    addq.l #1,%d2
    move.b 1(%a2),%d0
    cmpi.b #57,%d0 /* negative octave: next character is a digit */
    bls.s .line_next
    addq.l #1,%d2
.line_next:
    addq.l #1,%a2
    bra.w .line_character
.line_done:
    movem.l (%sp),%d2/%a2-%a3
    lea 12(%sp),%sp
    rts
.line_bitmap:
    move.l %d0,-(%sp)
    move.l %d2,-(%sp)
    pea 0x400bf10a
    move.l %a3,-(%sp)
    jsr 0x400128a8
    lea 16(%sp),%sp
    rts
    .balign 4
.line_sharp_bitmap: .long 3,5,1,.line_sharp_pixels,.line_sharp_mask
.line_sharp_pixels: .long 0xf8000000,0x50000000,0xf8000000
.line_sharp_mask: .long 0xf8000000,0xf8000000,0xf8000000
.line_dash_bitmap: .long 1,1,1,.line_dash_pixels,.line_dash_pixels
.line_dash_pixels: .long 0x80000000

/* Reserve the lower row for settings. Long add9 names omit their optional
 * parentheses in this view; the full chord identity remains in ch_name_text. */
    .global ch_draw_chord_name
ch_draw_chord_name:
    lea -12(%sp),%sp
    movem.l %d2/%a2-%a3,(%sp)
    move.l %a0,%a2
    move.l %a0,-(%sp)
    pea -1
    pea 0x400ba876
    jsr 0x40012f30
    lea 12(%sp),%sp
    cmpi.l #41,%d0
    bls.s .chord_name_draw
    move.l %a2,%a0
    lea ch_compact_name,%a3
    move.l %a3,%a2
.chord_name_copy:
    move.b (%a0)+,%d0
    beq.s .chord_name_end
    cmpi.b #40,%d0
    beq.s .chord_name_copy
    cmpi.b #41,%d0
    beq.s .chord_name_copy
    move.b %d0,(%a3)+
    bra.s .chord_name_copy
.chord_name_end:
    clr.b (%a3)
.chord_name_draw:
    move.l %a2,-(%sp)
    pea -1
    pea 17
    pea 78
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    movem.l (%sp),%d2/%a2-%a3
    lea 12(%sp),%sp
    rts

/* UI settings token: use the public getters, including AUTO's separate bit.
 * d0 track preserved, d1 token; a0 scratch. */
ch_settings_token:
    lea -12(%sp),%sp
    movem.l %d0/%d2-%d3,(%sp)
    move.l %d0,%d3
    jsr mh_voic_get
    move.l %d0,%d2
    move.l %d3,%d0
    jsr mh_sprd_get
    lsl.l #3,%d0
    or.l %d0,%d2
    move.l %d3,%d0
    jsr mh_root_get
    lsl.l #5,%d0
    or.l %d0,%d2
    move.l %d3,%d0
    jsr mh_size_get
    lsl.l #7,%d0
    or.l %d2,%d0
    move.l %d0,%d1
    movem.l (%sp),%d0/%d2-%d3
    lea 12(%sp),%sp
    rts

    .global ch_settings_text,ch_draw_settings,ch_settings_buffer
ch_settings_text: /* d0 track -> a0 compact N/V/S/R text */
    bsr.w ch_settings_token
    move.l %d1,%d0
    lsr.l #5,%d0
    andi.l #3,%d0
    lea .settings_roots,%a0
    move.l (%a0,%d0.l*4),-(%sp)
    move.l %d1,%d0
    lsr.l #3,%d0
    andi.l #3,%d0
    lea .settings_spreads,%a0
    move.l (%a0,%d0.l*4),-(%sp)
    move.l %d1,%d0
    andi.l #7,%d0
    lea .settings_voices,%a0
    move.l (%a0,%d0.l*4),-(%sp)
    lsr.l #7,%d1
    lea .settings_sizes,%a0
    move.l (%a0,%d1.l*4),-(%sp)
    pea .settings_format
    pea ch_settings_buffer
    jsr 0x40013a08
    lea 24(%sp),%sp
    lea ch_settings_buffer,%a0
    rts
ch_draw_settings:
    bsr.s ch_settings_text
    move.l %a0,-(%sp)
    pea -1
    pea 9
    pea 61
    pea 0x400bf10a
    pea 0x400ba876
    jsr 0x40012bd8
    lea 24(%sp),%sp
    rts
    .balign 4
.settings_voices: .long .svr,.sva,.sv1,.sv2,.sv3
.settings_spreads: .long .ssc,.sso,.ssw
.settings_roots: .long .srk,.sro,.sr1,.sr2
.settings_sizes: .long .snn,.sn2,.sn3,.sn4
.settings_format: .asciz "%s %s %s %s"
.snn: .asciz "N:N"
.sn2: .asciz "N:2"
.sn3: .asciz "N:3"
.sn4: .asciz "N:4"
.svr: .asciz "V:R"
.sva: .asciz "V:A"
.sv1: .asciz "V:1"
.sv2: .asciz "V:2"
.sv3: .asciz "V:3"
.ssc: .asciz "S:C"
.sso: .asciz "S:O"
.ssw: .asciz "S:W"
.srk: .asciz "R:K"
.sro: .asciz "R:O"
.sr1: .asciz "R:-1"
.sr2: .asciz "R:-2"
    .balign 4
ch_settings_buffer: .space 24
ch_compact_name: .space 32
