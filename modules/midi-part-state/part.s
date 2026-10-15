/* Shared native MIDI Part access, owned by MIDI PART STATE.
 * Harmony and Follow use the same implementation. No KITS references/hooks.
 * Context = bank * 4 + Part, 0..63; -1 means unavailable. Read/write take
 * explicit context so queued events never consult the current UI selection.
 * All public entries preserve every register except d0 and condition codes.
 */
    .include "remix.inc"
    .if MP_DEFINE
    .text
    .global mp_ui_context,mp_play_context,mp_read,mp_write,mp_read_key,mp_epoch
mp_ui_context:
    lea -12(%sp),%sp
    movem.l %d1-%d2/%a0,(%sp)
    move.l 0x46c82456,%d0
    subi.l #0x400e21e0,%d0
    cmpi.l #0x9b340*16,%d0
    bcc.s .ui_bad
    move.l %d0,%d2
    move.l #0x9b340,%d1
    divu.l %d1,%d0
    mulu.l %d0,%d1
    cmp.l %d1,%d2
    bne.s .ui_bad
    lsl.l #2,%d0
    moveq #0,%d1
    move.b 0x100b14cf,%d1
    cmpi.l #3,%d1
    bhi.s .ui_bad
    add.l %d1,%d0
    bra.s .ui_done
.ui_bad:
    moveq #-1,%d0
.ui_done:
    movem.l (%sp),%d1-%d2/%a0
    lea 12(%sp),%sp
    rts

/* d0 context -> replacement epoch, or -1. Runtime-only history invalidation;
 * ordinary single-field UI edits do not replace a Part or change its epoch. */
mp_epoch:
    cmpi.l #63,%d0
    bhi.s .epoch_bad
    move.l %a0,-(%sp)
    lea mp_part_epochs,%a0
    move.l (%a0,%d0.l*4),%d0
    move.l (%sp)+,%a0
    rts
.epoch_bad:
    moveq #-1,%d0
    rts

/* d0 track. Unlatched tracks use the engine's applied bank/Part, not UI. */
mp_play_context:
    lea -8(%sp),%sp
    movem.l %d1/%a0,(%sp)
    cmpi.l #7,%d0
    bhi.s .play_bad
    lea 0x8000182a,%a0
    moveq #0,%d1
    move.b (%a0,%d0.l),%d1
    lea 0x80001832,%a0
    move.b (%a0,%d0.l),%d0
    andi.l #255,%d0
    cmpi.l #15,%d1
    bhi.s .play_applied
    cmpi.l #3,%d0
    bls.s .play_pack
.play_applied:
    moveq #0,%d1
    move.b 0x80001828,%d1
    moveq #0,%d0
    move.b 0x80001829,%d0
    cmpi.l #15,%d1
    bhi.s .play_bad
    cmpi.l #3,%d0
    bhi.s .play_bad
.play_pack:
    lsl.l #2,%d1
    add.l %d1,%d0
    bra.s .play_done
.play_bad:
    moveq #-1,%d0
.play_done:
    movem.l (%sp),%d1/%a0
    addq.l #8,%sp
    rts

/* Internal: d0 track,d1 context,d2 SETUP offset -> a0 byte, a1 bank,
 * d0 offset within working-Part array, d4 Part. d0=-1 rejects invalid input.
 * Only the eight reserved positions are accessible through this interface.
 */
.address:
    cmpi.l #7,%d0
    bhi.s .address_bad
    cmpi.l #63,%d1
    bhi.s .address_bad
    cmpi.l #19,%d2
    bhi.s .address_bad
    move.l #0x000db028,%d4 /* bits 3,5,12,13,15,16,18,19 */
    btst %d2,%d4
    beq.s .address_bad
    move.l %d1,%d4
    andi.l #3,%d4
    move.l #36,%d5
    mulu.l %d5,%d0
    add.l %d2,%d0
    addi.l #0x4e2,%d0
    move.l #0x18b2,%d5
    mulu.l %d4,%d5
    add.l %d5,%d0
    move.l %d1,%d5
    lsr.l #2,%d5
    move.l #0x9b340,%d6
    mulu.l %d6,%d5
    lea 0x400e21e0,%a1
    adda.l %d5,%a1
    move.l %a1,%a0
    adda.l #0x8ed80,%a0
    adda.l %d0,%a0
    rts
.address_bad:
    moveq #-1,%d0
    rts

/* d0 track,d1 context,d2 field -> raw byte, or -1 for invalid input.
 * Decoders own field defaults and packed-subfield validation. */
mp_read:
    lea -20(%sp),%sp
    movem.l %d4-%d6/%a0-%a1,(%sp)
    bsr.w .address
    tst.l %d0
    bmi.s .read_done
    bsr.w .snapshot_address
    moveq #0,%d0
    move.b (%a0),%d0
.read_done:
    movem.l (%sp),%d4-%d6/%a0-%a1
    lea 20(%sp),%sp
    rts

/* Read native KEY (offset 17) without making it a writable custom field. */
mp_read_key:
    lea -24(%sp),%sp
    movem.l %d2/%d4-%d6/%a0-%a1,(%sp)
    moveq #16,%d2
    bsr.w .address
    tst.l %d0
    bmi.s .key_done
    bsr.w .snapshot_address
    moveq #0,%d0
    move.b 1(%a0),%d0
.key_done:
    movem.l (%sp),%d2/%d4-%d6/%a0-%a1
    lea 24(%sp),%sp
    rts

/* Internal address remap for an in-progress native bank/Part replacement.
 * .address supplied a1 bank,d4 Part,d0 byte offset in the working array.
 * Only readers use the snapshot; native/UI writes retain native authority.
 */
.snapshot_address:
    cmpa.l mp_snapshot_bank,%a1
    bne.s .snapshot_done
    move.l mp_snapshot_parts,%d5
    btst %d4,%d5
    beq.s .snapshot_done
    move.l #0x18b2-288,%d5
    mulu.l %d4,%d5
    neg.l %d5
    add.l %d0,%d5
    subi.l #0x4e2,%d5
    lea mp_snapshot,%a0
    adda.l %d5,%a0
.snapshot_done:
    rts

/* d0 track,d1 context,d2 field,d3 byte -> 1 accepted, 0 invalid.
 * Caller validates semantic range. Update only working state, its current
 * bank CS1 mirror and native dirty bits. Saved Parts/Kit library stay native.
 * A short interrupt mask makes the byte/mirror/dirty update indivisible.
 */
mp_write:
    lea -24(%sp),%sp
    movem.l %d4-%d7/%a0-%a1,(%sp)
    cmpi.l #127,%d3
    bhi.w .write_bad
    bsr.w .address
    tst.l %d0
    bmi.w .write_bad
    move.w %sr,%d7
    move.w #0x2700,%sr
    cmp.b (%a0),%d3
    beq.s .write_restore
    move.b %d3,(%a0)
    move.l %a1,%a0
    adda.l #0x95048,%a0
    bset %d4,(%a0)
    moveq #1,%d6
    move.l %a1,%a0
    adda.l #0x9b332,%a0
    move.l %d6,(%a0)
    /* CS1 mirrors the UI/current bank, identified by the native pointer. */
    cmpa.l 0x46c82456,%a1
    bne.s .write_restore
    lea 0x100a4ece,%a0
    move.b %d3,(%a0,%d0.l)
    bset %d4,0x100b145e
    move.l %d6,0x100f8598
.write_restore:
    move.w %d7,%sr
    moveq #1,%d0
    bra.s .write_done
.write_bad:
    moveq #0,%d0
.write_done:
    movem.l (%sp),%d4-%d7/%a0-%a1
    lea 24(%sp),%sp
    rts
    .endif
