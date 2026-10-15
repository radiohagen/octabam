/* CHRD vocabulary. A quality is an identity, never a stored NOT2-4 value.
 * 0 TRI, 1 7TH, 2 ADD9, 3 SUS2, 4 SUS4, 5 MAJ, 6 MIN, 7 DOM7.
 * ch_build: d0=root (already snapped), d1=quality, d2=scale mask,
 * d3=tonic, a0=four bytes. All registers preserved. Unused/overflow
 * voices duplicate the root for stock's deduplicating arp bitmap.
 * Scale-relative offsets count degrees above THIS root, not the tonic.
 */
    .text
    .global ch_build,ch_count,ch_quality_format,ch_names
ch_build:
    lea -36(%sp),%sp
    movem.l %d0-%d7/%a1,(%sp)
    cmpi.l #127,%d0
    bhi.w .build_done
    cmpi.l #7,%d1
    bls.s .build_valid
    moveq #0,%d1
.build_valid:
    move.b %d0,(%a0)
    move.b %d0,1(%a0)
    move.b %d0,2(%a0)
    move.b %d0,3(%a0)
    lea ch_intervals,%a1
    lea (%a1,%d1.l*4),%a1
    moveq #1,%d4
.build_voice:
    moveq #0,%d5
    move.b (%a1,%d4.l),%d5
    cmpi.l #255,%d5
    beq.s .build_done
    move.l %d0,%d6
    cmpi.l #5,%d1
    bcc.s .build_explicit
.build_degree:
    addq.l #1,%d6
    cmpi.l #127,%d6
    bhi.s .build_done
    move.l %d6,%d7
    sub.l %d3,%d7
    bpl.s .build_mod
    addi.l #12,%d7
.build_mod:
    cmpi.l #12,%d7
    blt.s .build_test
    subi.l #12,%d7
    bra.s .build_mod
.build_test:
    btst %d7,%d2
    beq.s .build_degree
    subq.l #1,%d5
    bne.s .build_degree
    bra.s .build_store
.build_explicit:
    add.l %d5,%d6
.build_store:
    cmpi.l #127,%d6
    bhi.s .build_done
    move.b %d6,(%a0,%d4.l)
    addq.l #1,%d4
    cmpi.l #4,%d4
    bne.s .build_voice
.build_done:
    movem.l (%sp),%d0-%d7/%a1
    lea 36(%sp),%sp
    rts

/* d0=quality -> complete voice count; clobbers a0 only. */
ch_count:
    cmpi.l #7,%d0
    bls.s .count_valid
    moveq #0,%d0
.count_valid:
    lea ch_counts,%a0
    move.b (%a0,%d0.l),%d0
    andi.l #255,%d0
    rts

ch_quality_format: /* stock formatter (buffer,value) */
    move.l 4(%sp),%a0
    move.l 8(%sp),%d0
    cmpi.l #7,%d0
    bls.s .format_valid
    moveq #0,%d0
.format_valid:
    lea ch_names,%a1
    move.l (%a1,%d0.l*4),%a1
.format_copy:
    move.b (%a1)+,(%a0)+
    bne.s .format_copy
    rts

ch_intervals:
    .byte 0,2,4,255
    .byte 0,2,4,6
    .byte 0,2,4,8
    .byte 0,1,4,255
    .byte 0,3,4,255
    .byte 0,4,7,255
    .byte 0,3,7,255
    .byte 0,4,7,10
ch_counts: .byte 3,4,4,3,3,3,3,4
    .balign 4
ch_names: .long .tri,.seventh,.add9,.sus2,.sus4,.major,.minor,.dom7
.tri: .asciz "TRI"
.seventh: .asciz "7TH"
.add9: .asciz "ADD9"
.sus2: .asciz "SUS2"
.sus4: .asciz "SUS4"
.major: .asciz "MAJ"
.minor: .asciz "MIN"
.dom7: .asciz "DOM7"
    .balign 4
    .global ch_current,ch_live,ch_sequence_quality,ch_live_get,ch_live_context,ch_sequence_context
ch_current: .space 8,0
ch_live: .space 8,0
ch_sequence_quality: .space 8,0

/* Physical keyboard input uses the selected Part. Only CHORD PLAY has a
 * latched variation; chromatic/grid input inherits the current Part default.
 * d0=track -> quality, all other registers preserved. */
ch_live_get:
    cmpi.l #7,%d0
    bhi.s .live_default
    move.l %d1,-(%sp)
    move.l 0x460d16f0,%d1
    cmpi.l #6,%d1
    movem.l (%sp),%d1
    lea 4(%sp),%sp
    bne.s .live_default
    tst.l 0x460d1736 /* grid recording uses stock keys, not CHORD PLAY variations */
    bne.s .live_default
    move.l %a0,-(%sp)
    lea ch_live,%a0
    move.b (%a0,%d0.l),%d0
    andi.l #255,%d0
    move.l (%sp)+,%a0
    rts
.live_default:
    jmp ch_base_get

ch_live_context: /* d0=track; preserve registers */
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,%d1
    bsr.s ch_live_get
    lea ch_live,%a0
    move.b %d0,(%a0,%d1.l)
    lea ch_current,%a0
    move.b %d0,(%a0,%d1.l)
    bra.s .context_done
ch_sequence_context:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    lea ch_sequence_quality,%a0
.context_copy:
    lea ch_current,%a1
    move.b (%a0,%d0.l),%d1
    move.b %d1,(%a1,%d0.l)
.context_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

    .global ch_final,ch_output_final
ch_final: /* root snapping happens before generation; explicit tones stay explicit */
    lea -8(%sp),%sp
    movem.l %d2/%a0,(%sp)
    lea ch_current,%a0
    bra.s .final_quality
ch_output_final:
    lea -8(%sp),%sp
    movem.l %d2/%a0,(%sp)
    move.l %d1,%d2
    lsl.l #2,%d2
    add.l %d1,%d2
    add.l %d2,%d2
    lea 0x46c77b1e,%a0
    move.b (%a0,%d2.l),%d2
    cmpi.b #1,%d2
    lea ch_sequence_quality,%a0
    bne.s .final_quality
    lea ch_live,%a0
.final_quality:
    moveq #0,%d2
    move.b (%a0,%d1.l),%d2
    cmpi.l #5,%d2
    bcs.s .final_scale
    cmpi.l #7,%d2
    bhi.s .final_scale
    movem.l (%sp),%d2/%a0
    lea 8(%sp),%sp
    rts
.final_scale:
    movem.l (%sp),%d2/%a0
    lea 8(%sp),%sp
    jmp mh_quant
