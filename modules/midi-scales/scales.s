/* Stock KEY values 0..24 retain their exact meaning. 25..84 append
 * Dorian, Phrygian, Lydian, Mixolydian, Locrian for C, then C#, ... B.
 * No new persistence: same Part byte, working mirror and live setup lane.
 */
    .text
    .include "remix.inc"
    .global ms_decode,ms_raw,ms_source,ms_snap,ms_encoder,ms_output,ms_format
ms_source:
.ifdef HAVE_FOLLOW
    jmp bf_source_resolve
.else
    rts
.endif
ms_source_ui:
.ifdef HAVE_FOLLOW
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    jsr bf_source_resolve_at
    move.l (%sp)+,%d1
.endif
    rts
ms_raw_ui:
.ifdef HAVE_FOLLOW
    lea -12(%sp),%sp
    movem.l %d1-%d3,(%sp)
    move.l %d0,%d2
    bsr.w ms_source_ui
    move.l %d0,%d3
    cmp.l %d2,%d0
    bne.s .ui_followed
    jsr mp_ui_context
    bra.s .ui_context
.ui_followed:
    jsr mp_play_context
.ui_context:
    move.l %d0,%d1
    move.l %d3,%d0
    jsr mp_read_key
    movem.l (%sp),%d1-%d3
    lea 12(%sp),%sp
    rts
.else
.ifdef HAVE_HARMONY
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    jsr mp_read_key
    move.l (%sp)+,%d1
    rts
.else
    bra.w ms_raw
.endif
.endif
/* d0 track -> effective native KEY byte. */
ms_raw:
    bsr.s ms_source
    move.l %d0,%d1
    lsl.l #6,%d0
    lea 0x46c76df1,%a0
    adda.l %d0,%a0
    moveq #0,%d0
    move.b (%a0,%d1.l*4),%d0
    rts
/* d0 raw KEY -> key<<2 | mode<<6; -1 OFF/invalid. */
ms_decode:
    tst.l %d0
    beq.s .decode_off
    cmpi.l #84,%d0
    bhi.s .decode_off
    subq.l #1,%d0
    move.l %a0,-(%sp)
    lea ms_decode_table,%a0
    move.w (%a0,%d0.l*2),%d0 /* upper word was zero after the range check */
    move.l (%sp)+,%a0
    rts
.decode_off:
    moveq #-1,%d0
    rts
/* d0 pitch, d1 raw KEY -> snapped pitch; all other regs preserved. */
ms_snap:
    lea -28(%sp),%sp
    movem.l %d1-%d5/%a0-%a1,(%sp)
    move.l %d0,%d2
    cmpi.l #127,%d2
    bhi.w .snap_done
    move.l %d1,%d0
    bsr.s ms_decode
    tst.l %d0
    bmi.s .snap_done
    move.l %d0,%d3
    lsr.l #2,%d3
    andi.l #15,%d3
    lsr.l #6,%d0
    lea ms_masks,%a0
    moveq #0,%d4
    move.w (%a0,%d0.l*2),%d4
    moveq #0,%d5
.snap_search:
    move.l %d2,%d0
    sub.l %d5,%d0
    bmi.s .snap_upper
    bsr.s .snap_degree
    bne.s .snap_found
.snap_upper:
    move.l %d2,%d0
    add.l %d5,%d0
    cmpi.l #127,%d0
    bhi.s .snap_next
    bsr.s .snap_degree
    bne.s .snap_found
.snap_next:
    addq.l #1,%d5
    bra.s .snap_search
.snap_found:
    move.l %d0,%d2
.snap_done:
    move.l %d2,%d0
    movem.l (%sp),%d1-%d5/%a0-%a1
    lea 28(%sp),%sp
    rts
.snap_degree:
    move.l %d0,%d1
    sub.l %d3,%d1
    bpl.s .snap_mod
    addi.l #12,%d1
.snap_mod:
    cmpi.l #12,%d1
    blt.s .snap_test
    subi.l #12,%d1
    bra.s .snap_mod
.snap_test:
    btst %d1,%d4
    rts

ms_encoder:
    moveq #5,%d1
    cmp.l %d0,%d1
    bne.w .encoder_other
    lea -20(%sp),%sp
    movem.l %d0-%d3/%a0,(%sp)
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    move.l %d0,%d2
    bsr.w ms_source_ui
    cmp.l %d2,%d0
    bne.w .encoder_locked
    bsr.w ms_raw_ui
    move.l %d0,%d2 /* previous raw */
    bsr.w ms_decode
    tst.l %d0
    bmi.s .encoder_off
    move.l %d0,%d1
    lsr.l #2,%d1
    andi.l #15,%d1
    lsr.l #6,%d0
    add.l %d1,%d0
    add.l %d1,%d1
    add.l %d1,%d0
    add.l %d1,%d1
    add.l %d1,%d0
    addq.l #1,%d0 /* ordinal OFF, Cmaj, Cdor, ... */
    bra.s .encoder_delta
.encoder_off:
    moveq #0,%d0
.encoder_delta:
    move.l %d0,-(%sp)
    moveq #5,%d0
    move.l %d5,%d1
    bsr.w ms_ui_delta
    move.l %d0,%d1
    move.l (%sp)+,%d0
    cmpi.l #84,%d1
    ble.s .encoder_delta_min
    moveq #84,%d1
.encoder_delta_min:
    cmpi.l #-84,%d1
    bge.s .encoder_sum
    moveq #-84,%d1
.encoder_sum:
    add.l %d1,%d0
    bpl.s .encoder_max
    moveq #0,%d0
.encoder_max:
    cmpi.l #84,%d0
    ble.s .encoder_raw
    moveq #84,%d0
.encoder_raw:
    tst.l %d0
    beq.s .encoder_adjust
    subq.l #1,%d0
    moveq #0,%d1
.encoder_div:
    cmpi.l #7,%d0
    blt.s .encoder_mode
    subq.l #7,%d0
    addq.l #1,%d1
    bra.s .encoder_div
.encoder_mode:
    tst.l %d0
    beq.s .encoder_major
    cmpi.l #5,%d0
    beq.s .encoder_minor
    cmpi.l #6,%d0
    bne.s .encoder_extra
    subq.l #1,%d0
.encoder_extra:
    move.l %d1,%d3
    lsl.l #2,%d1
    add.l %d3,%d1
    add.l %d1,%d0
    addi.l #24,%d0
    bra.s .encoder_adjust
.encoder_major:
    add.l %d1,%d1
    move.l %d1,%d0
    addq.l #1,%d0
    bra.s .encoder_adjust
.encoder_minor:
    add.l %d1,%d1
    move.l %d1,%d0
    addq.l #2,%d0
.encoder_adjust:
    sub.l %d2,%d0
    move.l %d0,%d5 /* stock setter writes all mirrors/dirty flags */
    movem.l (%sp),%d0-%d3/%a0
    lea 20(%sp),%sp
    jmp 0x4007a3ea
.encoder_locked:
    movem.l (%sp),%d0-%d3/%a0
    lea 20(%sp),%sp
    jmp 0x4007a6ba
.encoder_other:
    jmp 0x4007a4cc

ms_output:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
.ifdef HAVE_HARMONY
    move.l %d7,%d0
    jsr mh_active
    tst.l %d0
    bne.s .output_skip
.endif
    move.l %d7,%d0
    bsr.w ms_raw
    cmpi.l #24,%d0
    bls.s .output_stock
    move.l %d0,%d1
    moveq #0,%d0
    move.b (%a2),%d0
    bsr.w ms_snap
    move.b %d0,(%a2)
.output_skip:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    jmp 0x4009fb80
.output_stock:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    tst.l -64(%fp)
    ble.s .output_native_skip
    jmp 0x4009fb5e
.output_native_skip:
    jmp 0x4009fb80

/* Stock formatter: two five-byte strings (key, scale). */
ms_format:
    lea -8(%sp),%sp
    movem.l %d2/%a2,(%sp)
    move.l 12(%sp),%a2
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    bsr.w ms_raw_ui
    bsr.w ms_decode
    clr.l (%a2)
    clr.l 4(%a2)
    clr.w 8(%a2)
    tst.l %d0
    bmi.s .format_off
    move.l %d0,%d2
    lsr.l #2,%d0
    andi.l #15,%d0
    lea ms_keys,%a0
    move.w (%a0,%d0.l*2),(%a2)
    lsr.l #6,%d2
    lea ms_names,%a0
    move.l (%a0,%d2.l*4),%d0
    move.l %d0,5(%a2)
    bra.s .format_done
.format_off:
    move.l #0x4f464600,(%a2)
.format_done:
    movem.l (%sp),%d2/%a2
    lea 8(%sp),%sp
    rts
    .balign 2
ms_masks: .word 0xab5,0x6ad,0x5ab,0xad5,0x6b5,0x5ad,0x56b
/* Immutable native KEY mapping. Major/minor retain values 1..24;
 * the five additional modes follow in tonic order at 25..84. */
ms_decode_table:
    .set .decode_tonic,0
    .rept 12
    .word .decode_tonic*4,320+.decode_tonic*4
    .set .decode_tonic,.decode_tonic+1
    .endr
    .set .decode_tonic,0
    .rept 12
    .word 64+.decode_tonic*4,128+.decode_tonic*4,192+.decode_tonic*4
    .word 256+.decode_tonic*4,384+.decode_tonic*4
    .set .decode_tonic,.decode_tonic+1
    .endr
ms_keys: .ascii "C\0C#D\0D#E\0F\0F#G\0G#A\0A#B\0"
ms_names: .ascii "MAJ\0DOR\0PHR\0LYD\0MIX\0MIN\0LOC\0"
/* d0 physical encoder, d1 raw movement -> d0 choice delta.
 * Stock fixed-point detent accumulator; four counts per choice, at most one
 * choice per report. No push acceleration for these small enumerations. */
    .global ms_ui_delta
ms_ui_delta:
    cmpi.l #4,%d1
    ble.s .ui_delta_low
    moveq #4,%d1
.ui_delta_low:
    cmpi.l #-4,%d1
    bge.s .ui_delta_accumulate
    moveq #-4,%d1
.ui_delta_accumulate:
    pea 1024
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr 0x40032510
    lea 12(%sp),%sp
    rts
