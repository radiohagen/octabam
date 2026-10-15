/* MIDI Harmony for 1.40C. Settings and KEY belong to native Parts. */
    .text
    .include "remix.inc"
    .global mh_get,mh_set,mh_source,mh_quant,mh_generate,mh_sequence
    .global mh_boot,mh_defaults,mh_arp_encoder,mh_note_encoder,mh_draw_type,mh_type_format,mh_keyboard

/* Effective native KEY, decoded to key<<2 | mode<<6; -1 for OFF.
 * Standalone Harmony uses stock Major/Minor. MIDI Scales adds five modes.
 */
    .global mh_active,mh_scale_record
mh_scale_record:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_play_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w mh_scale_record_at
    move.l (%sp)+,%d1
    rts
    .global mh_scale_record_at
mh_scale_record_at:
    bsr.w mh_raw_key_at
    bra.w .record_decode
    .global mh_raw_key_at
mh_raw_key_at:
    lea -12(%sp),%sp
    movem.l %d1-%d3,(%sp)
    move.l %d0,%d2
    move.l %d1,%d3
    bsr.w mh_source_at
    cmp.l %d2,%d0
    beq.s .record_own_context
    move.l %d0,-(%sp)
    jsr mp_play_context
    move.l %d0,%d3
    move.l (%sp)+,%d0
.record_own_context:
    move.l %d3,%d1
    jsr mp_read_key
    movem.l (%sp),%d1-%d3
    lea 12(%sp),%sp
    rts
.record_decode:
.ifdef HAVE_SCALES
    jmp ms_decode
.else
    tst.l %d0
    beq.s .record_off
    cmpi.l #24,%d0
    bhi.s .record_off
    subq.l #1,%d0
    move.l %d0,%d1
    lsr.l #1,%d0
    lsl.l #2,%d0
    btst #0,%d1
    beq.s .record_done
    ori.l #320,%d0
.record_done:
    rts
.record_off:
    moveq #-1,%d0
    rts
.endif
mh_active:
    /* KEY OFF disables snapping, not the selected Harmony operation. */
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_play_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    jsr mh_get_at
    move.l (%sp)+,%d1
    tst.l %d0
    rts

/* d0 track, d1 root -> effective chord scale record.
 * With KEY OFF, use major intervals rooted at this exact unsnapped pitch.
 * Keep mh_scale_record's OFF sentinel for quantization and voice history. */
    .global mh_chord_scale
mh_chord_scale:
    move.l %d2,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_play_context
    move.l %d0,%d2
    move.l (%sp)+,%d0
    bsr.w mh_chord_scale_at
    move.l (%sp)+,%d2
    rts
    .global mh_chord_scale_at
mh_chord_scale_at: /* d0 track,d1 root,d2 context */
    move.l %d3,-(%sp)
    move.l %d1,%d3
    move.l %d2,%d1
    bsr.w mh_scale_record_at
    tst.l %d0
    bpl.s .chord_scale_done
    move.l %d3,%d0
.chord_scale_pc:
    cmpi.l #12,%d0
    bcs.s .chord_scale_major
    subi.l #12,%d0
    bra.s .chord_scale_pc
.chord_scale_major:
    lsl.l #2,%d0
.chord_scale_done:
    move.l (%sp)+,%d3
    rts

/* d0 track -> ultimate source, or original track on invalid/cyclic data.
 * Preserves d2+; usable without Follow in the build. */
mh_source:
.ifdef HAVE_FOLLOW
    jmp bf_source_resolve
.else
    rts
.endif
    .global mh_source_ui
mh_source_ui:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w mh_source_at
    move.l (%sp)+,%d1
    tst.l %d0
    rts
    .global mh_source_at
mh_source_at:
.ifdef HAVE_FOLLOW
    jmp bf_source_resolve_at
.else
    rts
.endif

/* d0 MIDI pitch, d1 track -> d0 snapped pitch, or unchanged if TYPE OFF.
 * All other regs preserved. Nearest degree; exact ties choose lower.
 */
mh_quant:
    move.l %d2,-(%sp)
    move.l %d0,-(%sp)
    move.l %d1,%d0
    jsr mp_play_context
    move.l %d0,%d2
    move.l (%sp)+,%d0
    bsr.w mh_quant_at
    move.l (%sp)+,%d2
    rts
    .global mh_quant_ui
mh_quant_ui:
    move.l %d2,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d2
    move.l (%sp)+,%d0
    bsr.w mh_quant_at
    move.l (%sp)+,%d2
    tst.l %d0
    rts
    .global mh_quant_at
mh_quant_at: /* d0 pitch,d1 track,d2 captured context; others preserved */
    lea -32(%sp),%sp
    movem.l %d1-%d5/%a0-%a1,(%sp)
    move.l %d2,28(%sp)
    move.l %d0,%d2
    cmpi.l #127,%d2
    bhi.w .quant_done
    move.l %d1,%d0
    move.l 28(%sp),%d1
    jsr mh_get_at
    beq.w .quant_done
    move.l %d1,%d0  /* d1 was clobbered by getter; reload input track */
    move.l (%sp),%d0
    move.l 28(%sp),%d1
    bsr.w mh_scale_record_at
    tst.l %d0
    bmi.w .quant_done
    move.l %d0,%d3
    lsr.l #2,%d3
    andi.l #15,%d3
    lsr.l #6,%d0
    lea mh_masks,%a1
    moveq #0,%d4
    move.w (%a1,%d0.l*2),%d4
    moveq #0,%d5
.quant_search:
    move.l %d2,%d0
    sub.l %d5,%d0
    bmi.s .quant_upper
    bsr.s .is_degree
    bne.s .quant_found
.quant_upper:
    move.l %d2,%d0
    add.l %d5,%d0
    cmpi.l #127,%d0
    bhi.s .quant_next
    bsr.s .is_degree
    bne.s .quant_found
.quant_next:
    addq.l #1,%d5
    cmpi.l #12,%d5
    blt.s .quant_search
    bra.s .quant_done
.quant_found:
    move.l %d0,%d2
.quant_done:
    move.l %d2,%d0
    movem.l (%sp),%d1-%d5/%a0-%a1
    lea 32(%sp),%sp
    rts
/* d0 note,d3 tonic,d4 mask -> Z false if degree. */
.is_degree:
    move.l %d0,%d1
    sub.l %d3,%d1
    bpl.s .pc_mod
    addi.l #12,%d1
.pc_mod:
    cmpi.l #12,%d1
    blt.s .pc_test
    subi.l #12,%d1
    bra.s .pc_mod
.pc_test:
    btst %d1,%d4
    rts

/* d0 track, d1 signed transpose, a0 four-byte stock scratch.
 * mh_generate resolves a followed root; mh_direct uses the supplied pitch.
 * Return 0 bypassed, 1 generated, -1 invalid root. Preserve other registers.
 * Transpose first, snap root, then stack scale thirds. Padding duplicates root
 * because stock's arp bitmap requires valid pitches and deduplicates them.
 */
mh_generate:
    lea -40(%sp),%sp
    movem.l %d1-%d7/%a0-%a1,(%sp)
    move.l %d0,%d7
    jsr mp_play_context
    move.l %d0,36(%sp)
    moveq #1,%d5
    bra.s .gen_start
    .global mh_direct
mh_direct:
    lea -40(%sp),%sp
    movem.l %d1-%d7/%a0-%a1,(%sp)
    move.l %d0,%d7
    jsr mp_ui_context
    move.l %d0,36(%sp)
    moveq #0,%d5
.gen_start:
    move.l %a0,%a1
    move.l %d7,%d0
    move.l 36(%sp),%d1
    jsr mh_get_at
    move.l %d0,%d6
    beq.w .gen_return
    moveq #0,%d2
    move.b (%a1),%d2
.ifdef HAVE_FOLLOW
    tst.l %d5
    beq.s .gen_own
    move.l %d7,%d0
    move.l 36(%sp),%d1
    bsr.w mh_source_at
    cmp.l %d7,%d0
    beq.s .gen_own
    move.l %d7,%d1
    jsr bf_register
    cmpi.l #256,%d0
    beq.s .gen_own
    move.l %d0,%d2
    add.l (%sp),%d2
    bra.s .gen_bounds /* Follow's signed octave must not wrap as a byte. */
.gen_own:
.endif
    /* A follower ignores its own degree, but an invalid own root must not
     * wrap into range when native TRAN arithmetic is applied. */
    cmpi.l #127,%d2
    bhi.w .gen_invalid
    add.l (%sp),%d2
    andi.l #255,%d2 /* Same byte arithmetic as stock TRAN/arranger. */
.gen_bounds:
    cmpi.l #127,%d2
    bhi.w .gen_invalid
    move.l %d2,%d0
    move.l %d7,%d1
    move.l 36(%sp),%d2
    bsr.w mh_quant_at
    move.l %d0,%d2
    move.b %d2,(%a1)
    move.b %d2,1(%a1)
    move.b %d2,2(%a1)
    move.b %d2,3(%a1)
    move.l %d7,%d0
    move.l %d2,%d1
    move.l 36(%sp),%d2
    bsr.w mh_chord_scale_at
    moveq #0,%d2
    move.b (%a1),%d2
    move.l %d0,%d5
    lsr.l #6,%d0
    lea mh_masks,%a0
    moveq #0,%d4
    move.w (%a0,%d0.l*2),%d4
    lsr.l #2,%d5
    andi.l #15,%d5
    /* d2 snapped root, d4 mask, d5 tonic. */
    moveq #1,%d0
    cmpi.l #1,%d6
    beq.w .gen_return
    lea ch_current,%a0
    moveq #0,%d1
    move.b (%a0,%d7.l),%d1
    move.l %d2,%d0
    move.l %d4,%d2
    move.l %d5,%d3
    move.l %a1,%a0
    jsr ch_build
    moveq #1,%d0
    bra.w .gen_return
.gen_invalid:
    clr.l (%a1) /* Safe bitmap input; sequence output is muted below. */
    moveq #-1,%d0
.gen_return:
    movem.l (%sp),%d1-%d7/%a0-%a1
    lea 40(%sp),%sp
    rts

mh_sequence:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    move.l %d7,%d0
    jsr ch_sequence_context
    moveq #0,%d1
    move.b 0x22c(%a5),%d1
    subi.l #64,%d1
    lea 0x46c7a124,%a0
    moveq #0,%d0
    move.b (%a0,%d7.l),%d0
    add.l %d0,%d1
    move.l %d7,%d0
    lea -4(%fp),%a0
    jsr hd_sequence_prepare
    bsr.w mh_generate
    lea ch_sequence_root,%a0
    move.b -4(%fp),%d1
    move.b %d1,(%a0,%d7.l)
    lea -4(%fp),%a0
    tst.l %d0
    ble.s .sequence_not_voiced
    move.l %d0,-(%sp)
    move.l %d7,%d0
    bsr.w mh_voice
    move.l (%sp)+,%d0
    moveq #0,%d1
    move.b -4(%fp),%d1
    cmpi.l #127,%d1
    bls.s .sequence_not_voiced
    clr.l -4(%fp) /* Empty OMIT pool: safe stock bitmap, muted output. */
    moveq #-1,%d0
.sequence_not_voiced:
    lea mh_muted,%a0
    clr.b (%a0,%d7.l)
    tst.l %d0
    bpl.s .sequence_ready
    moveq #1,%d0
    move.b %d0,(%a0,%d7.l)
.sequence_ready:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    move.l %fp,%d2
    subq.l #4,%d2
    move.l %d2,-(%sp)
    jmp 0x4009fa30

    .balign 2
mh_masks:
    .word 0xab5,0x6ad,0x5ab,0xad5,0x6b5,0x5ad,0x56b

/* Harmony replaces native key correction with its effective scale. */
    .global mh_scale
mh_scale:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    move.l %d7,%d0
    bsr.w mh_active
    beq.s .scale_stock
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    jmp 0x4009fad8
.scale_stock:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    move.b 49(%a0),%d0
    beq.s .scale_zero
    jmp 0x4009fade
.scale_zero:
    jmp 0x4009fad8

/* Follow captures raw NOTE + TRAN before snapping, in every HARM mode. */
    .global mh_prepare
mh_prepare:
    jmp hd_prepare
    rts

/* Final correction also keeps stock arp step offsets inside the scale. */
    .global mh_final,mh_output
mh_final:
    jmp ch_final
    .global mh_final_ui
mh_final_ui:
    lea -8(%sp),%sp
    movem.l %d2/%a0,(%sp)
    lea ch_current,%a0
    moveq #0,%d2
    move.b (%a0,%d1.l),%d2
    cmpi.l #5,%d2
    bcs.s .final_ui_scale
    cmpi.l #7,%d2
    bhi.s .final_ui_scale
    movem.l (%sp),%d2/%a0
    addq.l #8,%sp
    rts
.final_ui_scale:
    movem.l (%sp),%d2/%a0
    addq.l #8,%sp
    bra.w mh_quant_ui

/* Sequenced pools already contain TRAN from chord generation; do not add it
 * twice. Live pools contain absolute keyboard pitches, so their arp output
 * uses stock TRAN/arranger arithmetic on every tick. Direct keyboard output
 * never enters this hook and remains absolute, just like stock.
 * OFF replays stock arithmetic; KEY OFF leaves pitches unsnapped. Invalid sequenced roots are muted
 * after safely initializing the arp; live keyboard pools remain usable.
 */
    .global mh_transpose
mh_transpose:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    move.l %d7,%d0
    bsr.w mh_active
    beq.s .transpose_stock
    move.l %d7,%d0
    lsl.l #3,%d0
    lea 0x46c77b1e,%a0
    adda.l %d0,%a0
    move.l %d7,%d0
    add.l %d0,%d0
    move.b (%a0,%d0.l),%d0
    cmpi.b #1,%d0
    beq.s .transpose_stock
    lea mh_muted,%a0
    tst.b (%a0,%d7.l)
    bne.s .transpose_muted
.transpose_ready:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    jmp 0x4009fb58
.transpose_muted:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    jmp 0x4009fd2a
.transpose_stock:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    move.b 0x22c(%a5),%d0
    move.l %d1,%a1
    jmp 0x4009fb40

/* After stock transpose/scale and optional Follow, before note ownership. */
mh_output:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    moveq #0,%d0
    move.b (%a2),%d0
    move.l %d7,%d1
    jsr ch_output_final
    move.b %d0,(%a2)
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    move.b (%a2),%d1
    move.b %d1,%d3
    extb.l %d3
    move.l %d6,%d0
    add.l %d3,%d0
    jmp 0x4009fb8c

/* Settings live in native Parts. These hooks reset runtime state only. */
mh_reset:
    jsr mh_voice_clear
    rts
mh_defaults:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    bsr.s mh_reset
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    clr.l 0x100b14d8
    jmp 0x40025ace
mh_boot:
    jsr ch_lock_init
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    bsr.w mh_reset
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    move.b 0x100b14ae,%d0
    extb.l %d0
    jmp 0x4001022a

/* NOTE SETUP F TYPE. Follow's shared callback forwards every non-D knob
 * here; without Follow the stock callback pointer already names this entry.
 */
mh_note_encoder:
    move.l 4(%sp),%d0
    cmpi.l #5,%d0
    beq.s .type_ours
    lea -16(%sp),%sp
    movem.l %d2-%d3/%a2-%a3,(%sp)
    jmp 0x4003a8f0
.type_ours:
    move.l 8(%sp),%d1
    bsr.w mh_ui_delta
    move.l %d2,-(%sp)
    move.l %d0,-(%sp)
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    move.l %d2,%d0
    bsr.w mh_get
    move.l (%sp)+,%d1
    cmpi.l #2,%d1
    ble.s .type_delta_low
    moveq #2,%d1
.type_delta_low:
    cmpi.l #-2,%d1
    bge.s .type_add
    moveq #-2,%d1
.type_add:
    add.l %d1,%d0
    bpl.s .type_max
    moveq #0,%d0
.type_max:
    cmpi.l #2,%d0
    ble.s .type_set
    moveq #2,%d0
.type_set:
    move.l %d0,%d1
    move.l %d2,%d0
    bsr.w mh_set
    move.l (%sp)+,%d2
    jmp 0x40036548

mh_draw_type:
    cmpi.l #5,%d4
    bne.s .draw_type_done
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    bsr.w mh_get
    move.l %d0,%d3
    move.l %d3,60(%sp) /* compare to own value, never a pending Part edit */
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
.draw_type_done:
    move.l %d1,%d0
    lsl.l #4,%d0
    move.l %d0,%a0
    jmp 0x40036688
mh_type_format:
    move.l 4(%sp),%a0
    move.l 8(%sp),%d0
    cmpi.l #2,%d0
    bls.s .type_format_ok
    moveq #0,%d0
.type_format_ok:
    lea mh_types,%a1
    move.l (%a1,%d0.l*4),%a1
.type_copy:
    move.b (%a1)+,(%a0)+
    bne.s .type_copy
    rts
    .balign 4
mh_types: .long .off,.note,.triad
.off: .asciz "OFF"
.note: .asciz "NOTE"
.triad: .asciz "CHORD"
.seventh: .asciz "7TH"
    .balign 2

/* No new controls on ARP SETUP. Its native KEY is read-only on followers. */
mh_arp_encoder:
    move.l 4(%sp),%d0
    cmpi.l #5,%d0
    bne.s .arp_native
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    move.l %d0,%d1
    bsr.w mh_source_ui
    cmp.l %d1,%d0
    beq.s .arp_local
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    jmp 0x40079d48
.arp_local:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
.arp_native:
    lea -36(%sp),%sp
    movem.l %d2-%d7/%a2-%a4,(%sp)
    jmp 0x4007a2f4

/* Live keyboard: remember generated notes per physical pitch until release.
 * Shared chord tones are reference-counted, so releasing one key cannot stop
 * a tone still held by another. Changes to TYPE/KEY/SCALE never change offs.
 * Stock keeps channel/note ownership and handles arp insertion/removal.
 */
mh_keyboard:
    lea -44(%sp),%sp
    movem.l %d2-%d7/%a2-%a5,(%sp)
    move.l 48(%sp),%d2 /* track */
    move.l 52(%sp),%d3 /* physical pitch */
    move.l 56(%sp),%d4 /* velocity */
    move.l 60(%sp),%d5 /* recorder flag */
    cmpi.l #7,%d2
    bhi.w .keyboard_stock
    cmpi.l #127,%d3
    bhi.w .keyboard_stock
    move.l %d2,%d0
    lsl.l #7,%d0
    add.l %d3,%d0
    lea mh_held,%a3
    lea (%a3,%d0.l*4),%a3
    move.l %d2,%d0
    lsl.l #7,%d0
    lea mh_refs,%a4
    adda.l %d0,%a4
    move.l (%a3),%d0
    cmpi.l #0xfeffffff,%d0 /* This key was pressed while Harmony was bypassed. */
    beq.w .keyboard_was_stock
    cmpi.l #-1,%d0
    beq.s .keyboard_new
    bsr.w mh_release
    tst.l %d4
    beq.w .keyboard_done
.keyboard_new:
    move.l %d2,%d0
    jsr mh_get
    beq.w .keyboard_passthrough
    move.l %d0,%d6
    tst.l %d4
    beq.w .keyboard_done
    move.l %d2,%d0
    jsr ch_live_context
    lea 40(%sp),%a2
    move.b %d3,(%a2)
    /* All keyboard modes choose an absolute root and inherit only scale. */
    move.l %d2,%d0
    moveq #0,%d1
    move.l %a2,%a0
    bsr.w mh_direct
.ifdef HAVE_FOLLOW
    moveq #0,%d0
    move.b (%a2),%d0
    move.l %d2,%d1
    bsr.w mh_final_ui
    bsr.w mh_latch_key_root
.endif
    /* The root latch above must see the musical root, never the inversion. */
    move.l %d2,%d0
    move.l %a2,%a0
    bsr.w mh_voice_ui
    /* Record the physical key once, independently of snapping/live voices. */
    move.l %d5,-(%sp)
    move.l %d4,-(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    bsr.w mh_record_key
    lea 16(%sp),%sp
    moveq #0,%d6
.keyboard_voice:
    moveq #0,%d0
    move.b (%a2,%d6.l),%d0
    move.l %d2,%d1
    bsr.w mh_final_ui
    moveq #-1,%d1
    move.b %d1,(%a3,%d6.l)
    cmpi.l #127,%d0
    bhi.s .keyboard_next
    /* Deduplicate the generator's padding; count only one owner per key. */
    moveq #0,%d1
.keyboard_duplicate:
    cmp.l %d6,%d1
    beq.s .keyboard_send
    cmp.b (%a3,%d1.l),%d0
    beq.s .keyboard_next
    addq.l #1,%d1
    bra.s .keyboard_duplicate
.keyboard_send:
    move.b %d0,(%a3,%d6.l)
    /* A key pressed in bypass can already own this generated tone. Adopt
     * it before adding another owner, rather than letting its release cut
     * the new chord short. Its physical-key recorder identity is retained. */
    tst.b (%a4,%d0.l)
    bne.s .keyboard_count
    move.l %d2,%d1
    lsl.l #7,%d1
    add.l %d0,%d1
    lea mh_held,%a0
    lea (%a0,%d1.l*4),%a0
    move.l (%a0),%d1
    cmpi.l #0xfeffffff,%d1
    bne.s .keyboard_count
    move.l #-1,(%a0)
    move.b %d0,(%a0)
    moveq #1,%d1
    move.b %d1,(%a4,%d0.l)
    move.l %d0,-(%sp)
    move.l %d0,%d1
    move.l %d2,%d0
    jsr mh_adopt_key
    move.l (%sp)+,%d0
.keyboard_count:
    moveq #0,%d1
    move.b (%a4,%d0.l),%d1
    addq.l #1,%d1
    move.b %d1,(%a4,%d0.l)
    cmpi.b #1,%d1
    bne.s .keyboard_next
    clr.l -(%sp) /* Generated voices sound, but never enter the recorder. */
    move.l %d4,-(%sp)
    move.l %d0,-(%sp)
    move.l %d2,-(%sp)
    jsr mh_owned_key
    lea 16(%sp),%sp
.keyboard_next:
    addq.l #1,%d6
    cmpi.l #4,%d6
    bne.w .keyboard_voice
    move.l (%a3),%d0
    cmpi.l #-1,%d0
    bne.s .keyboard_done
    move.l #0xfdffffff,(%a3) /* Silent key still owns a recorder release. */
    bra.s .keyboard_done
.keyboard_was_stock:
    moveq #-1,%d0
    move.l %d0,(%a3)
    tst.l %d4
    beq.s .keyboard_stock
    move.l %d2,%d0
    jsr mh_get
    beq.s .keyboard_passthrough
    /* Repeated press: release the old stock note before changing ownership. */
    move.l %d5,-(%sp)
    clr.l -(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    bsr.w mh_stock_key
    lea 16(%sp),%sp
    bra.w .keyboard_new
.keyboard_passthrough:
    tst.l %d4
    beq.w .keyboard_stock
    /* Bypass pressed over an existing chord tone joins its ownership.
     * Unrelated bypass notes continue through the unmodified stock path. */
    tst.b (%a4,%d3.l)
    beq.s .keyboard_native_press
    move.l #-1,(%a3)
    move.b %d3,(%a3)
    moveq #0,%d1
    move.b (%a4,%d3.l),%d1
    addq.l #1,%d1
    move.b %d1,(%a4,%d3.l)
    move.l %d5,-(%sp)
    move.l %d4,-(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    bsr.w mh_record_key
    lea 16(%sp),%sp
    bra.s .keyboard_done
.keyboard_native_press:
.ifdef HAVE_FOLLOW
    /* Bypass still publishes the physical root; do not change the stock
     * sender/recorder arguments or quantize a HARM OFF / KEY OFF key. */
    move.l %d3,%d0
    bsr.w mh_latch_key_root
.endif
    move.l #0xfeffffff,(%a3)
    bra.s .keyboard_stock
.keyboard_done:
    movem.l (%sp),%d2-%d7/%a2-%a5
    lea 44(%sp),%sp
    rts
.keyboard_stock:
    movem.l (%sp),%d2-%d7/%a2-%a5
    lea 44(%sp),%sp
mh_stock_key:
    lea -28(%sp),%sp
    movem.l %d2-%d7/%a2,(%sp)
    jmp 0x4009e9b0
.ifdef HAVE_FOLLOW
/* d0=logical pitch, d2=track. Note-ons only; releases never change the root. */
mh_latch_key_root:
    cmpi.l #127,%d0
    bhi.s .key_root_done
    lea bf_pitches,%a1
    move.b %d0,(%a1,%d2.l) /* preserve source octave for MIDI Follow */
.key_root_mod:
    cmpi.l #12,%d0
    blt.s .key_root_store
    subi.l #12,%d0
    bra.s .key_root_mod
.key_root_store:
    addi.l #36,%d0
    lea bf_roots,%a1
    move.b %d0,(%a1,%d2.l)
.key_root_done:
    rts
.endif
/* Stock recorder tail, without transmitting or owning a MIDI voice.
 * Same four arguments and saved-register frame as mh_stock_key. Resolve
 * the native Part channel exactly as 0x4009e9c0..0x4009e9f8, then enter its
 * recorder handoff. Additional chord voices must not enqueue more roots.
 */
    .global mh_record_key
mh_record_key:
    lea -28(%sp),%sp
    movem.l %d2-%d7/%a2,(%sp)
    move.l 44(%sp),%d7
    tst.l %d7
    beq.s .record_key_done
    move.l 32(%sp),%d5
    move.l 36(%sp),%d3
    move.l 40(%sp),%d6
    move.l 0x46c82456,%a1
    moveq #0,%d0
    move.b 0x100b14cf,%d0
    move.l %d5,%d1
    lsl.l #5,%d1
    move.l %d1,%a2
    lea (%a2,%d5.l*4),%a0
    move.l #0x18b2,%d2
    muls.l %d2,%d0
    adda.l %d0,%a0
    lea (%a1,%a0.l),%a0
    adda.l #0x8f262,%a0
    moveq #0,%d4
    move.b (%a0),%d4
    beq.s .record_key_handoff /* Stock permits recording with CHAN OFF. */
    subq.l #1,%d4
    andi.l #15,%d4
.record_key_handoff:
    jmp 0x4009eb7a
.record_key_done:
    movem.l (%sp),%d2-%d7/%a2
    lea 28(%sp),%sp
    rts

mh_release:
    moveq #0,%d0
    move.b (%a3),%d0
    cmpi.l #253,%d0
    beq.s .release_record
    cmpi.l #127,%d0
    bhi.s .release_begin
.release_record:
    move.l %d5,-(%sp)
    clr.l -(%sp)
    move.l %d3,-(%sp) /* Same physical pitch as the recorder note-on. */
    move.l %d2,-(%sp)
    bsr.w mh_record_key
    lea 16(%sp),%sp
.release_begin:
    moveq #0,%d6
.release_voice:
    moveq #0,%d0
    move.b (%a3,%d6.l),%d0
    cmpi.l #127,%d0
    bhi.s .release_next
    moveq #-1,%d1
    move.b %d1,(%a3,%d6.l)
    tst.b (%a4,%d0.l)
    beq.s .release_next
    moveq #0,%d1
    move.b (%a4,%d0.l),%d1
    subq.l #1,%d1
    move.b %d1,(%a4,%d0.l)
    bne.s .release_next
    clr.l -(%sp) /* Recorder release was emitted once, above. */
    clr.l -(%sp)
    move.l %d0,-(%sp)
    move.l %d2,-(%sp)
    jsr mh_owned_key
    lea 16(%sp),%sp
.release_next:
    addq.l #1,%d6
    cmpi.l #4,%d6
    bne.s .release_voice
    moveq #-1,%d0
    move.l %d0,(%a3)
    rts
    .balign 4
    .global mh_muted
mh_muted: .space 8,0
    .global mh_held
mh_held: .space 4096,255
mh_refs: .space 1024,0


    .global mh_draw_key
mh_draw_key:
    move.b (%a0),%d4
    cmpi.l #5,%d3
    bne.s .draw_key_done
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    moveq #0,%d0
    move.b 0x100b14cc,%d0
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w mh_raw_key_at
    move.l %d0,%d4
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
.draw_key_done:
    move.l %d3,%d0
    moveq #3,%d2
    jmp 0x4007a1b6

/* d0 physical encoder, d1 raw movement -> d0 choice delta.
 * Stock fixed-point detent accumulator; four counts per choice, at most one
 * choice per report. No push acceleration for these small enumerations. */
    .global mh_ui_delta
mh_ui_delta:
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
