/* Automatic voice leading and chord spacing. d0=track, a0=four generated pitches.
 * Called only AFTER Follow captures the harmonic root. Never touches NOTE,
 * recorder arguments, or bf_roots. Preserves all input registers.
 *
 * Enumerate each inversion at octave offsets 0,-12,+12, rejecting pitches
 * outside MIDI and bass notes more than an octave from the requested root.
 * Cost = 8 * sum(abs(new[i]-previous[i])) + number of moving voices.
 * This first minimizes total movement, then maximizes held common voices.
 * Exact ties prefer root position, then the earlier inversion/offset.
 * Score the actual spread pitches, not an unspread intermediate chord.
 * Root jumps of >=12 semitones shift the reference by their whole-octave
 * component (toward zero). Small root moves retain ordinary voice leading.
 * History's token high byte holds the previous logical root, not the bass.
 * First chord/context change seeds root position with the chosen spread. Incomplete top-of-MIDI
 * chords keep the generator's omission behavior and invalidate history.
 */
    .text
    .global mh_voice,mh_voice_history,mh_voice_clear
mh_voice_clear:
    lea mh_voice_history,%a0
    moveq #16,%d0
.vc_loop:
    clr.l (%a0)+
    subq.l #1,%d0
    bne.s .vc_loop
    rts

    .global mh_voice_ui,mh_voice_at
mh_voice:
    lea -92(%sp),%sp
    movem.l %d0-%d7/%a0-%a4,(%sp)
    jsr mp_play_context
    bra.s .voice_context
mh_voice_ui:
    lea -92(%sp),%sp
    movem.l %d0-%d7/%a0-%a4,(%sp)
    jsr mp_ui_context
    bra.s .voice_context
mh_voice_at: /* d0 track,d1 captured context,a0 pool; all regs preserved */
    lea -92(%sp),%sp
    movem.l %d0-%d7/%a0-%a4,(%sp)
    move.l %d1,%d0
.voice_context:
    move.l %d0,88(%sp)
    move.l (%sp),%d0
    cmpi.l #7,%d0
    bhi.w .voice_done
    move.l %d0,%d7
    move.l %a0,%a4
    lea mh_voice_history,%a2
    lsl.l #3,%d0
    adda.l %d0,%a2
    move.l 88(%sp),%d1
    moveq #16,%d2
    move.l %d7,%d0
    jsr mp_read
    move.l 88(%sp),%d1
    lsl.l #8,%d1
    or.l %d1,%d0
    lea mh_voice_context,%a0
    cmp.l (%a0,%d7.l*4),%d0
    beq.s .voice_context_ready
    move.l %d0,(%a0,%d7.l*4)
    clr.l 4(%a2)
.voice_context_ready:
    move.l 88(%sp),%d0
    jsr mp_epoch
    lea mh_voice_epoch,%a0
    cmp.l (%a0,%d7.l*4),%d0
    beq.s .voice_epoch_ready
    move.l %d0,(%a0,%d7.l*4)
    clr.l 4(%a2)
.voice_epoch_ready:
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_voic_get_at
    move.l %d0,80(%sp)
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_sprd_get_at
    move.l %d0,76(%sp)
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_get_at
    cmpi.l #2,%d0
    blt.w .voice_reset
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_size_get_at
    tst.l %d0
    bne.w .voice_fixed
    lea ch_current,%a0
    moveq #0,%d0
    move.b (%a0,%d7.l),%d0
    jsr ch_count
    move.l %d0,%d6
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_scale_record_at
    tst.l %d0
    bpl.s .voice_scale_token
    move.l #0x3ff,%d0 /* distinct no-scale context, below source/count bits */
.voice_scale_token:
    move.l %d0,%d5
    lea ch_current,%a0
    moveq #0,%d0
    move.b (%a0,%d7.l),%d0
    lsl.l #8,%d0
    lsl.l #5,%d0
    or.l %d0,%d5
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_source_at
    lsl.l #8,%d0
    lsl.l #2,%d0
    or.l %d0,%d5
    move.l %d6,%d0
    swap %d0
    or.l %d0,%d5 /* token = count<<16 | source<<10 | effective scale */
    move.l 76(%sp),%d0
    swap %d0
    lsl.l #4,%d0
    or.l %d0,%d5 /* include spread in the history context */
    move.l %d5,72(%sp)
    move.l (%a4),52(%sp) /* immutable root-position input */
    move.l (%a4),56(%sp) /* best chord */
    lea 52(%sp),%a3
    moveq #0,%d3
    moveq #-1,%d1
.voice_validate:
    moveq #0,%d0
    move.b (%a3,%d3.l),%d0
    cmpi.l #127,%d0
    bhi.w .voice_partial
    cmp.l %d1,%d0
    ble.w .voice_partial
    move.l %d0,%d1
    addq.l #1,%d3
    cmp.l %d6,%d3
    blt.s .voice_validate
    lea 56(%sp),%a0
    move.l 80(%sp),%d0
    cmpi.l #2,%d0
    blt.s .voice_apply_spread
    subq.l #1,%d0
    bsr.w mh_invert
.voice_apply_spread:
    move.l 76(%sp),%d0
    bsr.w mh_spread /* Failure leaves CLOSE intact at the MIDI ceiling. */
    move.l 80(%sp),%d0
    cmpi.l #1,%d0
    bne.w .voice_remember
    move.l 72(%sp),%d5
    move.l 4(%a2),%d0
    andi.l #0x00ffffff,%d0 /* root register is not a context change */
    cmp.l %d0,%d5
    bne.w .voice_remember
    moveq #0,%d0
    move.b (%a3),%d0
    move.l %d0,68(%sp) /* anchor root */
    moveq #0,%d1
    move.b 4(%a2),%d1 /* previous logical root in token's high byte */
    cmp.l %d1,%d0
    bne.s .voice_new_root
    move.l (%a2),56(%sp) /* Repeated root/quality keeps the sounded voicing. */
    bra.w .voice_remember
.voice_new_root:
    sub.l %d1,%d0
    moveq #0,%d1
.voice_register_up:
    cmpi.l #12,%d0
    blt.s .voice_register_down
    subi.l #12,%d0
    addi.l #12,%d1
    bra.s .voice_register_up
.voice_register_down:
    cmpi.l #-12,%d0
    bgt.s .voice_register_ready
    addi.l #12,%d0
    subi.l #12,%d1
    bra.s .voice_register_down
.voice_register_ready:
    move.l %d1,84(%sp) /* signed reference shift; never stored as a pitch */
    move.l #0x7fffffff,%d0
    move.l %d0,64(%sp)
    moveq #0,%d4 /* inversion */
.voice_inversion:
    moveq #0,%d5 /* octave offset, ordered 0,-12,+12 */
.voice_candidate:
    moveq #0,%d2 /* score */
    moveq #0,%d3 /* voice */
.voice_pitch:
    move.l %d4,%d1
    add.l %d3,%d1
    moveq #0,%d0
    cmp.l %d6,%d1
    blt.s .voice_unwrapped
    sub.l %d6,%d1
    moveq #12,%d0
.voice_unwrapped:
    add.l %d5,%d0
    moveq #0,%d7
    move.b (%a3,%d1.l),%d7
    add.l %d7,%d0
    tst.l %d3
    beq.s .candidate_range
    moveq #0,%d7
    move.b 60(%sp),%d7
.candidate_raise:
    cmp.l %d7,%d0
    bge.s .candidate_reduce
    addi.l #12,%d0
    bra.s .candidate_raise
.candidate_reduce:
    addi.l #12,%d7
.candidate_lower:
    cmp.l %d7,%d0
    blt.s .candidate_range
    subi.l #12,%d0
    bra.s .candidate_lower
.candidate_range:
    cmpi.l #127,%d0
    bhi.w .voice_next_octave /* unsigned comparison rejects negatives too */
    tst.l %d3
    bne.s .voice_distance
    move.l %d0,%d1
    sub.l 68(%sp),%d1
    bpl.s .voice_anchor
    neg.l %d1
.voice_anchor:
    cmpi.l #12,%d1
    bgt.w .voice_next_octave
.voice_distance:
    lea 60(%sp),%a0
    move.b %d0,(%a0,%d3.l)
    addq.l #1,%d3
    cmp.l %d6,%d3
    blt.s .voice_pitch
    bsr.w mh_sort_chord
    move.l 76(%sp),%d0
    bsr.w mh_spread
    tst.l %d0
    beq.w .voice_next_octave
    /* Only score candidates containing the exact requested root register.
     * ROOT placement still runs afterward; Follow and recording use the
     * untouched logical root. This prevents gradual octave walking. */
    moveq #0,%d3
.voice_root_find:
    moveq #0,%d0
    move.b (%a0,%d3.l),%d0
    cmp.l 68(%sp),%d0
    beq.s .voice_root_found
    addq.l #1,%d3
    cmp.l %d6,%d3
    blt.s .voice_root_find
    bra.w .voice_next_octave
.voice_root_found:
    moveq #0,%d0
    move.b (%a0),%d0
    sub.l 68(%sp),%d0
    bpl.s .voice_sounded_anchor
    neg.l %d0
.voice_sounded_anchor:
    cmpi.l #12,%d0
    bgt.w .voice_next_octave
    moveq #0,%d3
.voice_score:
    moveq #0,%d0
    move.b (%a0,%d3.l),%d0
    moveq #0,%d1
    move.b (%a2,%d3.l),%d1
    add.l 84(%sp),%d1
    sub.l %d1,%d0
    beq.s .voice_same
    bpl.s .voice_positive
    neg.l %d0
.voice_positive:
    lsl.l #3,%d0
    addq.l #1,%d0
    add.l %d0,%d2
.voice_same:
    addq.l #1,%d3
    cmp.l %d6,%d3
    blt.s .voice_score
    cmp.l 64(%sp),%d2
    bge.s .voice_next_octave
    move.l %d2,64(%sp)
    move.l 60(%sp),56(%sp)
.voice_next_octave:
    tst.l %d5
    bgt.s .voice_next_inversion
    beq.s .voice_lower
    moveq #12,%d5
    bra.w .voice_candidate
.voice_lower:
    moveq #-12,%d5
    bra.w .voice_candidate
.voice_next_inversion:
    addq.l #1,%d4
    cmp.l %d6,%d4
    blt.w .voice_inversion
.voice_remember:
    cmpi.l #3,%d6
    bne.s .voice_copy
    move.b 56(%sp),59(%sp) /* triad padding duplicates lowest voice */
.voice_copy:
    move.l 56(%sp),(%a4)
    move.l 56(%sp),(%a2)
    move.l 72(%sp),4(%a2)
    move.b 52(%sp),4(%a2) /* preserve root independently of chosen inversion */
    move.l 80(%sp),%d0
    cmpi.l #1,%d0
    beq.s .voice_omit
.voice_partial:
    clr.l 4(%a2)
.voice_omit:
    move.l (%sp),%d0 /* original track, not the search scratch register */
    move.l 88(%sp),%d1
    jsr mh_root_get_at
    tst.l %d0
    beq.s .voice_done
    moveq #0,%d1
    move.b 52(%sp),%d1 /* original harmonic root, before inversion */
    move.l %a4,%a0
    bsr.w mh_root_apply
    bra.s .voice_done
.voice_fixed: /* Fixed SIZE shares history/reset boundaries, not NAT recipes. */
    lsl.l #7,%d0
    move.l %d0,%d6
    or.l 80(%sp),%d6
    move.l 76(%sp),%d0
    lsl.l #3,%d0
    or.l %d0,%d6
    move.l %d7,%d0
    move.l 88(%sp),%d1
    jsr mh_root_get_at
    lsl.l #5,%d0
    or.l %d0,%d6
    move.l %d7,%d0
    jsr mh_scale_record_at
    tst.l %d0
    bpl.s .fixed_scale
    move.l #0x3ff,%d0
.fixed_scale:
    move.l %d0,%d5
    move.l %d7,%d0
    jsr mh_source_at
    lsl.l #8,%d0
    lsl.l #2,%d0
    or.l %d0,%d5
    lea ch_current,%a0
    moveq #0,%d0
    move.b (%a0,%d7.l),%d0
    move.l %d5,-(%sp)
    move.l %d0,-(%sp)
    move.l %d6,-(%sp)
    move.l %a2,-(%sp)
    move.l %a4,-(%sp)
    jsr mh_size_voice_c
    lea 20(%sp),%sp
    bra.s .voice_done
.voice_reset:
    clr.l 4(%a2)
.voice_done:
    movem.l (%sp),%d0-%d7/%a0-%a4
    lea 92(%sp),%sp
    rts
/* d0 ROOT mode, d1 original logical root, a0 voiced four-byte pool.
 * Move the existing root, never add a voice. Anchor to the logical root,
 * not its inverted/spread register. Below MIDI zero, omit that root.
 * AUTO history deliberately remains the full upper voicing, as with OMIT.
 */
    .global mh_root_apply
mh_root_apply:
    tst.l %d0
    beq.w .root_apply_done
    lea -32(%sp),%sp
    movem.l %d0-%d5/%a1,(%sp)
    move.l %d1,%d5
    cmpi.l #1,%d0
    beq.s .root_apply_omit
    subi.l #12,%d5
    cmpi.l #3,%d0
    bne.s .root_apply_omit
    subi.l #12,%d5
.root_apply_omit:
    bsr.w mh_omit_root
    cmpi.l #1,%d0
    beq.s .root_apply_return
    tst.l %d5
    bmi.s .root_apply_return
    lea 28(%sp),%a1
    move.b %d5,(%a1)
    moveq #1,%d3
    moveq #0,%d2
.root_apply_next:
    moveq #0,%d4
    move.b (%a0,%d2.l),%d4
    cmpi.l #127,%d4
    bhi.s .root_apply_skip
    moveq #0,%d1
.root_apply_duplicate:
    moveq #0,%d0
    move.b (%a1,%d1.l),%d0
    cmp.l %d4,%d0
    beq.s .root_apply_skip
    addq.l #1,%d1
    cmp.l %d3,%d1
    blt.s .root_apply_duplicate
    cmpi.l #4,%d3
    bge.s .root_apply_skip
    move.b %d4,(%a1,%d3.l)
    addq.l #1,%d3
.root_apply_skip:
    addq.l #1,%d2
    cmpi.l #4,%d2
    blt.s .root_apply_next
.root_apply_pad:
    cmpi.l #4,%d3
    bge.s .root_apply_copy
    move.b %d5,(%a1,%d3.l)
    addq.l #1,%d3
    bra.s .root_apply_pad
.root_apply_copy:
    move.l (%a1),(%a0)
.root_apply_return:
    movem.l (%sp),%d0-%d5/%a1
    lea 32(%sp),%sp
.root_apply_done:
    rts

/* Remove the harmonic root pitch class from all four pool entries.
 * Fill unused slots by duplicating the lowest remaining tone for stock arp.
 * An empty result is all FF: sequence converts it to a safe muted pool;
 * keyboard skips invalid notes but still records/releases the physical key.
 */
    .global mh_omit_root
mh_omit_root:
    lea -24(%sp),%sp
    movem.l %d0-%d4,(%sp)
    moveq #-1,%d0
    move.l %d0,20(%sp)
.omit_root_mod:
    cmpi.l #12,%d1
    blt.s .omit_root_start
    subi.l #12,%d1
    bra.s .omit_root_mod
.omit_root_start:
    moveq #0,%d2
    moveq #0,%d3
.omit_root_next:
    moveq #0,%d4
    move.b (%a0,%d2.l),%d4
    cmpi.l #127,%d4
    bhi.s .omit_root_skip
    move.l %d4,%d0
.omit_note_mod:
    cmpi.l #12,%d0
    blt.s .omit_note_test
    subi.l #12,%d0
    bra.s .omit_note_mod
.omit_note_test:
    cmp.l %d1,%d0
    beq.s .omit_root_skip
    move.b %d4,20(%sp,%d3.l)
    addq.l #1,%d3
.omit_root_skip:
    addq.l #1,%d2
    cmpi.l #4,%d2
    blt.s .omit_root_next
    tst.l %d3
    beq.s .omit_root_copy
    move.b 20(%sp),%d0
.omit_root_pad:
    cmpi.l #4,%d3
    bge.s .omit_root_copy
    move.b %d0,20(%sp,%d3.l)
    addq.l #1,%d3
    bra.s .omit_root_pad
.omit_root_copy:
    move.l 20(%sp),(%a0)
    movem.l (%sp),%d0-%d4
    lea 24(%sp),%sp
    rts

/* Manual inversion: d0=1..3, d6=count, a0=sorted complete root chord.
 * Clamp to count-1 (3RD on a triad uses 2ND). Raise each rotated note by
 * enough octaves to sit above the chosen bass, then sort. This preserves
 * the selected inversion for an ADD9 whose ninth crosses the octave. Atomic fallback to root position if any pitch exceeds 127.
 * Registers preserved. Spread is applied afterward by the caller.
 */
    .global mh_invert
mh_invert:
    lea -28(%sp),%sp
    movem.l %d0-%d4/%a1,(%sp)
    cmp.l %d6,%d0
    blt.s .invert_start
    move.l %d6,%d0
    subq.l #1,%d0
.invert_start:
    move.l (%a0),24(%sp)
    lea 24(%sp),%a1
    moveq #0,%d2
.invert_pitch:
    move.l %d0,%d1
    add.l %d2,%d1
    moveq #0,%d3
    cmp.l %d6,%d1
    blt.s .invert_unwrapped
    sub.l %d6,%d1
    moveq #12,%d3
.invert_unwrapped:
    moveq #0,%d4
    move.b (%a0,%d1.l),%d4
    add.l %d4,%d3
    moveq #0,%d4
    move.b (%a0,%d0.l),%d4 /* requested bass */
.invert_raise:
    cmp.l %d4,%d3
    bge.s .invert_reduce
    addi.l #12,%d3
    bra.s .invert_raise
.invert_reduce:
    addi.l #12,%d4
.invert_lower:
    cmp.l %d4,%d3
    blt.s .invert_range
    subi.l #12,%d3
    bra.s .invert_lower
.invert_range:
    cmpi.l #127,%d3
    bhi.s .invert_done
    move.b %d3,(%a1,%d2.l)
    addq.l #1,%d2
    cmp.l %d6,%d2
    blt.s .invert_pitch
    move.l (%a1),(%a0)
    bsr.w mh_sort_chord
.invert_done:
    movem.l (%sp),%d0-%d4/%a1
    lea 28(%sp),%sp
    rts

/* d0 spread, d6 count, a0 sorted close chord. d0=success; other regs
 * preserved. OPEN lifts the second-lowest voice an octave and sorts it to
 * the end. WIDE lifts every voice above the bass one octave. No partial
 * writes: an out-of-range result leaves the supplied close chord intact.
 */
    .global mh_spread
mh_spread:
    lea -20(%sp),%sp
    movem.l %d1-%d3/%a1,(%sp)
    move.l (%a0),16(%sp)
    lea 16(%sp),%a1
    tst.l %d0
    beq.s .spread_ok
    cmpi.l #1,%d0
    bne.s .spread_wide
    moveq #0,%d2
    move.b 1(%a1),%d2
    addi.l #12,%d2
    cmpi.l #127,%d2
    bhi.s .spread_fail
    moveq #2,%d1
.spread_rotate:
    move.b (%a1,%d1.l),%d3
    move.b %d3,-1(%a1,%d1.l)
    addq.l #1,%d1
    cmp.l %d6,%d1
    blt.s .spread_rotate
    move.b %d2,-1(%a1,%d6.l)
    bra.s .spread_ok
.spread_wide:
    moveq #1,%d1
.spread_upper:
    moveq #0,%d2
    move.b (%a1,%d1.l),%d2
    addi.l #12,%d2
    cmpi.l #127,%d2
    bhi.s .spread_fail
    move.b %d2,(%a1,%d1.l)
    addq.l #1,%d1
    cmp.l %d6,%d1
    blt.s .spread_upper
.spread_ok:
    /* Sort the completed spacing before publishing it atomically. */
    move.l %a0,-(%sp)
    move.l %a1,%a0
    bsr.w mh_sort_chord
    move.l (%sp)+,%a0
    move.l (%a1),(%a0)
    moveq #1,%d0
    bra.s .spread_return
.spread_fail:
    moveq #0,%d0
.spread_return:
    movem.l (%sp),%d1-%d3/%a1
    lea 20(%sp),%sp
    rts
    .balign 4
mh_voice_history: .space 64,0
mh_voice_context: .space 32,0xff

/* Sort only the sounding voices; triad padding is handled by the caller.
 * d6 count, a0 four pitches. Preserve all registers. */
    .text
mh_sort_chord:
    lea -20(%sp),%sp
    movem.l %d0-%d4,(%sp)
    move.l %d6,%d4
.sort_pass:
    moveq #0,%d3 /* Already sorted candidates need only one pass. */
    moveq #1,%d2
.sort_pair:
    moveq #0,%d0
    moveq #0,%d1
    move.b -1(%a0,%d2.l),%d0
    move.b (%a0,%d2.l),%d1
    cmp.l %d1,%d0
    bls.s .sort_next
    move.b %d1,-1(%a0,%d2.l)
    move.b %d0,(%a0,%d2.l)
    moveq #1,%d3
.sort_next:
    addq.l #1,%d2
    cmp.l %d4,%d2
    blt.s .sort_pair
    tst.l %d3
    beq.s .sort_done
    subq.l #1,%d4
    cmpi.l #1,%d4
    bgt.s .sort_pass
.sort_done:
    movem.l (%sp),%d0-%d4
    lea 20(%sp),%sp
    rts


    .balign 4
mh_voice_epoch: .space 32,0xff
