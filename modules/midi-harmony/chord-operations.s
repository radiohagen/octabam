    .include "remix.inc"
/* CHRD mirrors native MIDI editing operations and their clipboard/undo
 * destinations. Audio-track copies deliberately have no CHRD counterpart.
 */
    .text
    .global ch_memcpy,ch_clear_locks,ch_clear_track,ch_place,ch_step_copy,ch_step_paste
.ui_bank:
    move.l 0x46c82456,%d0
    subi.l #0x400e21e0,%d0
    move.l #0x9b340,%d1
    divu.l %d1,%d0
    rts
.touch:
    bsr.s .ui_bank
    jmp ch_nv_save
ch_place:
    lsl.l #4,%d6
    move.l %a5,%d3
    add.l %d6,%d3
    lea -20(%sp),%sp
    movem.l %d0-%d2/%d4/%a0,(%sp)
    bsr.s .ui_bank
    moveq #0,%d1
    move.b 0x100b14d0,%d1
    moveq #0,%d2
    move.b 0x100b14cc,%d2
    move.l #255,%d4
    jsr hd_forget
    jsr ch_lock_set
    movem.l (%sp),%d0-%d2/%d4/%a0
    lea 20(%sp),%sp
    jmp 0x4005fd90
ch_clear_locks:
    lea -32(%sp),%sp
    movem.l %d0-%d6/%a0,(%sp)
    bsr.w .ui_bank
    move.l 36(%sp),%d1
    move.l 40(%sp),%d2
    moveq #0,%d3
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .clear_locks_done
    moveq #0,%d5
    move.b 47(%sp),%d5
    lsl.l #4,%d5
    moveq #0,%d6
    move.w 50(%sp),%d6
    moveq #0,%d3
    moveq #-1,%d4
.clear_locks_loop:
    btst %d3,%d6
    beq.s .clear_locks_next
    move.l %d5,%d0
    add.l %d3,%d0
    cmpi.l #63,%d0
    bhi.s .clear_locks_next
    move.b %d4,(%a0,%d0.l)
    lea -20(%sp),%sp
    movem.l %d0-%d3/%a0,(%sp)
    move.l %d0,%d3
    bsr.w .ui_bank
    move.l 56(%sp),%d1
    move.l 60(%sp),%d2
    jsr hd_forget
    movem.l (%sp),%d0-%d3/%a0
    lea 20(%sp),%sp
.clear_locks_next:
    addq.l #1,%d3
    cmpi.l #16,%d3
    bne.s .clear_locks_loop
    bsr.w .touch
.clear_locks_done:
    movem.l (%sp),%d0-%d6/%a0
    lea 32(%sp),%sp
    lea -44(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40040d4c
ch_clear_track:
    move.l 12(%sp),%d0
    btst #0,%d0
    beq.s .clear_track_stock
    lea -20(%sp),%sp
    movem.l %d0-%d3/%a0,(%sp)
    bsr.w .ui_bank
    move.l 24(%sp),%d1
    move.l 28(%sp),%d2
    moveq #0,%d3
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .clear_track_done
    moveq #-1,%d0
    moveq #16,%d1
.clear_track_loop:
    move.l %d0,(%a0)+
    subq.l #1,%d1
    bne.s .clear_track_loop
    bsr.w .ui_bank
    move.l 24(%sp),%d1
    move.l 28(%sp),%d2
    moveq #0,%d3
.clear_degrees_loop:
    jsr hd_forget
    addq.l #1,%d3
    cmpi.l #64,%d3
    bne.s .clear_degrees_loop
    bsr.w .touch
.clear_track_done:
    movem.l (%sp),%d0-%d3/%a0
    lea 20(%sp),%sp
.clear_track_stock:
    lea -56(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x40039b08

.buf_of:
    lea ch_clip,%a1
    cmpi.l #0x460c8122,%d0
    beq.s .buf_done
    lea ch_undo,%a1
    cmpi.l #0x460bf218,%d0
    beq.s .buf_done
    suba.l %a1,%a1
.buf_done:
    rts
ch_step_copy:
    jsr hd_step_copy
    lea -36(%sp),%sp
    movem.l %d0-%d6/%a0-%a1,(%sp)
    bsr.w .ui_bank
    move.l 44(%sp),%d1
    move.l 48(%sp),%d2
    moveq #0,%d3
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .step_copy_done
    move.l 40(%sp),%d0
    bsr.s .buf_of
    move.l %a1,%d0
    beq.s .step_copy_done
    moveq #0,%d4
    move.b 55(%sp),%d4
    lsl.l #4,%d4
    moveq #0,%d5
    move.w 58(%sp),%d5
    moveq #0,%d6
.step_copy_loop:
    btst %d6,%d5
    beq.s .step_copy_next
    move.l %d4,%d0
    add.l %d6,%d0
    cmpi.l #63,%d0
    bhi.s .step_copy_next
    move.b (%a0,%d0.l),%d1
    move.b %d1,(%a1,%d6.l)
.step_copy_next:
    addq.l #1,%d6
    cmpi.l #16,%d6
    bne.s .step_copy_loop
.step_copy_done:
    movem.l (%sp),%d0-%d6/%a0-%a1
    lea 36(%sp),%sp
    lea -56(%sp),%sp
    movem.l %d2-%d7/%a2-%fp,(%sp)
    jmp 0x4002bd34
/* MIDI paste: a5 buffer, d3 source page bit, d4 destination step,
 * original sp+96 pattern, sp+100 track. */
ch_step_paste:
    lea -28(%sp),%sp
    movem.l %d0-%d5/%a0,(%sp)
    move.l %a1,-(%sp)
    move.l %a5,%d0
    bsr.w .buf_of
    move.l %a1,%d0
    beq.s .paste_done
    moveq #0,%d5
    move.b (%a1,%d3.l),%d5
    bsr.w .ui_bank
    move.l 128(%sp),%d1
    move.l 132(%sp),%d2
    move.l %d4,%d3
    move.l %d5,%d4
    jsr ch_lock_set
.paste_done:
    move.l (%sp)+,%a1
    movem.l (%sp),%d0-%d5/%a0
    lea 28(%sp),%sp
    adda.l #0x1001614e,%a1
    jmp 0x4002c73c

/* d0 native base, d2 byte count -> a0 CHRD base or null.
 * Preserves a1 (source counterpart while resolving destination). */
.locate:
    move.l %d0,%d1
    lea ch_clip,%a0
    subi.l #0x460c8122,%d1
    beq.w .loc_done
    move.l %d0,%d1
    lea ch_undo,%a0
    subi.l #0x460bf218,%d1
    beq.w .loc_done
    suba.l %a0,%a0
    subi.l #0x400e21e0,%d0
    cmpi.l #16*0x9b340,%d0
    bcc.w .loc_done
    move.l #0x9b340,%d4
    move.l %d0,%d1
    divu.l %d4,%d0
    mulu.l %d0,%d4
    sub.l %d4,%d1
    move.l %d0,%d3 /* bank */
    move.l #0x8ed8,%d4
    move.l %d1,%d0
    divu.l %d4,%d0
    cmpi.l #15,%d0
    bhi.s .loc_done
    mulu.l %d0,%d4
    sub.l %d4,%d1
    lsl.l #4,%d3
    add.l %d0,%d3 /* bank*16+pattern */
    lsl.l #3,%d3
    cmpi.l #0x8ed8,%d2
    bne.s .loc_track
    tst.l %d1
    bne.s .loc_done
    bra.s .loc_valid
.loc_track:
    subi.l #0x48d0,%d1
    cmpi.l #8*0x8b0,%d1
    bcc.s .loc_done
    move.l #0x8b0,%d4
    move.l %d1,%d0
    divu.l %d4,%d0
    mulu.l %d0,%d4
    cmp.l %d1,%d4
    bne.s .loc_done
    add.l %d0,%d3
.loc_valid:
    lsl.l #6,%d3
    lea ch_lock_table,%a0
    adda.l %d3,%a0
.loc_done:
    rts
ch_memcpy:
    move.l 12(%sp),%d0
    cmpi.l #0x8b0,%d0
    beq.s .copy_owned
    cmpi.l #0x8ed8,%d0
    bne.w .copy_stock
.copy_owned:
    lea -24(%sp),%sp
    movem.l %d2-%d5/%a2-%a3,(%sp)
    move.l %d0,%d2
    move.l 32(%sp),%d0
    bsr.w .locate
    move.l %a0,%d0
    beq.s .copy_done
    move.l %a0,%a2
    move.l 28(%sp),%d0
    bsr.w .locate
    move.l %a0,%d0
    beq.s .copy_done
    move.l %a0,%a3
    moveq #16,%d5
    cmpi.l #0x8ed8,%d2
    bne.s .copy_loop
    move.l #128,%d5
.copy_loop:
    move.l (%a2)+,(%a3)+
    subq.l #1,%d5
    bne.s .copy_loop
    move.l %a0,%d0
    subi.l #ch_lock_table,%d0
    cmpi.l #131072,%d0
    bcc.s .copy_done
    lsr.l #8,%d0
    lsr.l #5,%d0
    cmp.l ch_nv_bank,%d0
    bne.s .copy_done
    jsr ch_nv_save
.copy_done:
    movem.l (%sp),%d2-%d5/%a2-%a3
    lea 24(%sp),%sp
.copy_stock:
    jmp hd_memcpy
    .bss
    .balign 4
ch_clip: .space 512
ch_undo: .space 512

    .text
    .global ch_bitmap_all,ch_bitmap_step
ch_bitmap_step:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    move.l %d3,%d0
    move.l %d2,%d1
    bsr.s .bitmap_one
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    movem.l (%sp),%d2-%d4
    lea 12(%sp),%sp
    jmp 0x40033bc2
ch_bitmap_all:
    moveq #0,%d2
.bitmap_track:
    moveq #0,%d3
.bitmap_key:
    move.l %d2,%d0
    move.l %d3,%d1
    bsr.s .bitmap_one
    addq.l #1,%d3
    cmpi.l #64,%d3
    bne.s .bitmap_key
    addq.l #1,%d2
    cmpi.l #8,%d2
    bne.s .bitmap_track
    movem.l (%sp),%d2-%d7/%a2-%fp
    lea 44(%sp),%sp
    jmp 0x40033ab4
/* d0 track,d1 step. Native bitmap has already included all native locks. */
.bitmap_one:
    lea -20(%sp),%sp
    movem.l %d0-%d3/%a0,(%sp)
    move.l %d0,%d2
    move.l %d1,%d3
    bsr.w .ui_bank
    moveq #0,%d1
    move.b 0x100b14d0,%d1
    jsr ch_lock_ptr
    move.l %a0,%d0
    beq.s .bitmap_done
    moveq #0,%d0
    move.b (%a0),%d0
    cmpi.l #7,%d0
    bhi.s .bitmap_done
    lea 0x46c7d2e4,%a0
    moveq #0,%d0
    move.b (%a0,%d3.l),%d0
    bset %d2,%d0
    move.b %d0,(%a0,%d3.l)
.bitmap_done:
    movem.l (%sp),%d0-%d3/%a0
    lea 20(%sp),%sp
    rts
