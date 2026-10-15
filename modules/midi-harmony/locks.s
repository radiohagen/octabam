    .include "remix.inc"
/* Dedicated CHRD locks: bank x pattern x MIDI track x step.
 * Native NOTE / NOT2-4 / CC bytes are never storage for this module.
 * 0xff is unlocked; the reader inherits that pattern's Part CHRD default.
 * The current bank has a packed CS1 mirror, with a generation ticket to
 * prevent an engine writer from committing over a preempting UI writer.
 * The manifest owns this SRAM. Shared retention and HARMONY PLOCKS
 * compose with PLOCKS P2 without overlapping either checkpoint.
 */
    .set CH_BANK_BYTES,8192
    .set CH_BYTES,131072
    .text
    .global ch_lock_init,ch_lock_ptr,ch_lock_get,ch_lock_set,ch_lock_table
    .global ch_nv_save,ch_nv_restore,ch_nv_bank,ch_lock_status
ch_lock_init:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    move.l ch_initialized,%d0
    cmpi.l #0x43485244,%d0
    beq.s .init_done
    lea ch_lock_table,%a0
    move.l #CH_BYTES/4,%d1
    moveq #-1,%d0
.init_fill:
    move.l %d0,(%a0)+
    subq.l #1,%d1
    bne.s .init_fill
    /* Runtime BSS can contain the compressed loader's staging bytes.
     * Initialize message ownership once, before any producer can post. */
    lea ch_messages,%a0
    move.l #4096/4,%d1
    moveq #0,%d0
.init_messages:
    move.l %d0,(%a0)+
    subq.l #1,%d1
    bne.s .init_messages
    move.l %d0,ch_record_overflow
    move.l #0x43485244,%d0
    move.l %d0,ch_initialized
    jsr hd_reset
.init_done:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    rts

/* d0 bank, d1 pattern, d2 track, d3 step -> a0 (0 for invalid).
 * All input registers preserved. No lazy init in an ISR lookup.
 */
ch_lock_ptr:
    suba.l %a0,%a0
    cmpi.l #15,%d0
    bhi.s .ptr_done
    cmpi.l #15,%d1
    bhi.s .ptr_done
    cmpi.l #7,%d2
    bhi.s .ptr_done
    cmpi.l #63,%d3
    bhi.s .ptr_done
    move.l %d4,-(%sp)
    move.l %d0,%d4
    lsl.l #4,%d4
    add.l %d1,%d4
    lsl.l #3,%d4
    add.l %d2,%d4
    lsl.l #6,%d4
    add.l %d3,%d4
    lea ch_lock_table,%a0
    adda.l %d4,%a0
    move.l (%sp)+,%d4
.ptr_done:
    rts
ch_lock_get:
    move.l %d0,-(%sp)
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .get_invalid
    moveq #0,%d0
    move.b (%a0),%d0
    cmpi.l #7,%d0
    bls.s .get_done
.get_default:
    move.l (%sp),%d0
    jsr ch_base_pattern
    bra.s .get_done
.get_invalid:
    moveq #0,%d0
.get_done:
    addq.l #4,%sp
    rts

/* Same indices, d4=quality or 255. All registers preserved.
 * Invalid inputs have no writes. Caller marks the native bank dirty.
 */
ch_lock_set:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    cmpi.l #7,%d4
    bls.s .set_valid
    cmpi.l #255,%d4
    bne.s .set_done
.set_valid:
    jsr ch_lock_ptr
    move.l %a0,%d1
    beq.s .set_done
    move.b %d4,(%a0)
    cmp.l ch_nv_bank,%d0
    bne.s .set_done
    jsr ch_nv_save
.set_done:
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    rts

/* d0=bank. Writes a full current-bank snapshot (no sparse capacity cap).
 * Header: magic committed last, version, bank, size, sum, generation.
 * A torn snapshot is rejected; the companion file is the recovery source.
 * Long interrupt masks would delay the audio ISR, so only ticket/commit
 * are protected. Generation mismatch restarts using the newest bank.
 */
ch_nv_save:
    jmp hd_nv_save
/* d0 bank -> d0=1 restored, 0 invalid; other registers preserved. */
ch_nv_restore:
    jmp hd_nv_restore
    .balign 4
ch_initialized: .long 0
ch_nv_bank: .long -1
ch_lock_status: .space 16,0
    .bss
    .balign 4
ch_lock_table: .space CH_BYTES
