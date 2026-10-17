/* Degree/register codec. Native NOTE bytes never contain this encoding.
 * code = 7 * (tonic_octave + 2) + zero_based_degree, 0..83.
 * The extra low octave admits C-1 as degree 2 above B-2, for example.
 * 0xff remains the unlocked sentinel. MIDI 60 is C4.
 * Scale ABI matches mh_scale_record: tonic<<2 | mode<<6; -1 = C major.
 * Encode snaps nearest, lower on ties. Decode returns -1 outside MIDI.
 * d0=value,d1=scale -> d0=result; all other registers preserved.
 */
    .text
    .global hd_encode,hd_decode,hd_format
    .global hd_encode_c,hd_decode_c
hd_encode_c:
    move.l 4(%sp),%d0
    move.l 8(%sp),%d1
    bra.w hd_encode
hd_decode_c:
    move.l 4(%sp),%d0
    move.l 8(%sp),%d1
    bra.w hd_decode
hd_decode:
    lea -24(%sp),%sp
    movem.l %d1-%d5/%a0,(%sp)
    cmpi.l #83,%d0
    bhi.w .decode_bad
    bsr.w .scale
    mulu.w #7,%d3
    lea hd_scale_degrees,%a0
    adda.l %d3,%a0
    move.l %d0,%d2
    moveq #7,%d1
    divu.l %d1,%d0
    move.l %d0,%d3
    mulu.l %d1,%d3
    sub.l %d3,%d2 /* degree 0..6 */
    subq.l #1,%d0
    moveq #12,%d1
    muls.l %d1,%d0
    add.l %d5,%d0 /* tonic pitch */
    moveq #0,%d3
    move.b (%a0,%d2.l),%d3
    add.l %d3,%d0
    cmpi.l #127,%d0
    bls.s .decode_done
.decode_bad:
    moveq #-1,%d0
.decode_done:
    movem.l (%sp),%d1-%d5/%a0
    lea 24(%sp),%sp
    rts

hd_encode:
    lea -28(%sp),%sp
    movem.l %d1-%d6/%a0,(%sp)
    cmpi.l #127,%d0
    bhi.w .encode_bad
    bsr.w .scale
    move.l %d0,%d6
    bsr.w .member
    bne.s .encode_found
    moveq #1,%d2
.encode_search:
    move.l %d6,%d0
    sub.l %d2,%d0
    bsr.w .member
    bne.s .encode_found
    move.l %d6,%d0
    add.l %d2,%d0
    bsr.w .member
    bne.s .encode_found
    addq.l #1,%d2
    cmpi.l #12,%d2
    bcs.s .encode_search
    bra.s .encode_bad
.encode_found:
    sub.l %d5,%d0
    moveq #-1,%d1
    tst.l %d0
    bpl.s .encode_positive
    addi.l #12,%d0
    bra.s .encode_register
.encode_positive:
    move.l %d0,%d1
    moveq #12,%d3
    divu.l %d3,%d1
    mulu.l %d1,%d3
    sub.l %d3,%d0 /* scale semitone 0..11 */
.encode_register:
    addq.l #1,%d1
    moveq #7,%d3
    mulu.l %d3,%d1
    moveq #0,%d2
    moveq #0,%d3
.encode_count:
    cmp.l %d0,%d3
    beq.s .encode_result
    btst %d3,%d4
    beq.s .encode_next
    addq.l #1,%d2
.encode_next:
    addq.l #1,%d3
    bra.s .encode_count
.encode_result:
    move.l %d1,%d0
    add.l %d2,%d0
    bra.s .encode_done
.encode_bad:
    moveq #-1,%d0
.encode_done:
    movem.l (%sp),%d1-%d6/%a0
    lea 28(%sp),%sp
    rts

/* d1 -> d3 mode,d4 mask,d5 tonic. Invalid scale falls back to C major.
 * Does not modify d0/d2. Both public callers preserve d3. */
.scale:
    moveq #0,%d4
    moveq #0,%d5
    tst.l %d1
    bmi.s .scale_mask
    move.l %d1,%d4
    lsr.l #6,%d4
    cmpi.l #6,%d4
    bhi.s .scale_fallback
    move.l %d1,%d5
    lsr.l #2,%d5
    andi.l #15,%d5
    cmpi.l #11,%d5
    bls.s .scale_mask
.scale_fallback:
    moveq #0,%d4
    moveq #0,%d5
.scale_mask:
    move.l %d4,%d3
    lea hd_masks,%a0
    move.w (%a0,%d4.l*2),%d4
    rts

/* d0 pitch,d4 mask,d5 tonic -> Z=0 for valid degree. d3 clobbered. */
.member:
    cmpi.l #127,%d0
    bhi.s .member_no
    move.l %d0,%d3
    sub.l %d5,%d3
    bpl.s .member_mod
    addi.l #12,%d3
.member_mod:
    cmpi.l #12,%d3
    bcs.s .member_test
    subi.l #12,%d3
    bra.s .member_mod
.member_test:
    btst %d3,%d4
    rts
.member_no:
    moveq #0,%d3
    rts

/* Native formatter (char *buffer, int code); no stock formatter needed. */
hd_format:
    lea -16(%sp),%sp
    movem.l %d2-%d3/%a0-%a1,(%sp)
    move.l 20(%sp),%a0
    move.l 24(%sp),%d0
    cmpi.l #83,%d0
    bhi.s .format_unlocked
    move.l %d0,%d1
    moveq #7,%d2
    divu.l %d2,%d0
    mulu.l %d0,%d2
    sub.l %d2,%d1
    addi.l #49,%d1
    move.b %d1,(%a0)+
    move.b #58,(%a0)+
    subq.l #2,%d0
    bpl.s .format_octave
    move.b #45,(%a0)+
    neg.l %d0
.format_octave:
    addi.l #48,%d0
    move.b %d0,(%a0)+
    clr.b (%a0)
    bra.s .format_done
.format_unlocked:
    move.b #45,(%a0)+
    move.b #45,(%a0)+
    clr.b (%a0)
.format_done:
    movem.l (%sp),%d2-%d3/%a0-%a1
    lea 16(%sp),%sp
    rts
    .balign 4
hd_masks: .word 0xab5,0x6ad,0x5ab,0xad5,0x6b5,0x5ad,0x56b
hd_scale_degrees:
    .byte 0,2,4,5,7,9,11
    .byte 0,2,3,5,7,9,10
    .byte 0,1,3,5,7,8,10
    .byte 0,2,4,6,7,9,11
    .byte 0,2,4,5,7,9,10
    .byte 0,2,3,5,7,8,10
    .byte 0,1,3,5,6,8,10
