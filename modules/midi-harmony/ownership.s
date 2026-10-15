/* Generated keyboard tones need independent release tokens per track.
 * Stock's live slot is indexed by pitch alone, even across MIDI channels.
 * Redirect only calls whose return address proves mh_owned_key ownership;
 * native keyboard callers retain the original table. No shared active-call
 * flag, temporary stock-memory swap, or interrupt mask is needed.
 */
    .text
    .global mh_owned_key,mh_key_tokens,mh_adopt_key
    .global mh_key_slot_on,mh_key_slot_arp,mh_key_slot_off,mh_key_slot_clear

/* C ABI (track,pitch,velocity,record=0). Caller already records physical keys.
 * Direct voices on a shared channel/pitch coalesce across tracks. Arp pools
 * stay per track and stock retains ownership of their sequenced output.
 */
mh_owned_key:
    lea -24(%sp),%sp
    movem.l %d2-%d5/%a2-%a3,(%sp)
    move.l 28(%sp),%d2
    move.l 32(%sp),%d3
    move.l 36(%sp),%d4
    lea mh_key_tokens,%a2
    move.l %d2,%d0
    lsl.l #8,%d0
    adda.l %d0,%a2
    lea (%a2,%d3.l*2),%a2
    tst.l %d4
    beq.s .owned_release
    /* Resolve the same Part channel and arp mode as the stock keyboard. */
    move.l 0x46c82456,%a0
    moveq #0,%d0
    move.b 0x100b14cf,%d0
    move.l #0x18b2,%d1
    muls.l %d1,%d0
    adda.l %d0,%a0
    adda.l #0x8f000,%a0
    move.l %d2,%d0
    lsl.l #5,%d0
    lea (%a0,%d0.l),%a1
    tst.b 0x170(%a1)
    bne.s .owned_call
    lea (%a1,%d2.l*4),%a1
    moveq #0,%d5
    move.b 0x262(%a1),%d5
    beq.s .owned_call
    subq.l #1,%d5
    andi.l #15,%d5
    ori.l #0x200,%d5
    bra.s .owned_share
.owned_release:
    moveq #0,%d5
    move.w (%a2),%d5
    cmpi.w #-1,%d5
    beq.w .owned_done
    btst #10,%d5
    bne.s .owned_call
.owned_share:
    lea mh_key_tokens,%a3
    lea (%a3,%d3.l*2),%a3
    moveq #8,%d0
.owned_scan:
    cmpa.l %a2,%a3
    beq.s .owned_next
    cmp.w (%a3),%d5
    bne.s .owned_next
    tst.l %d4
    beq.s .owned_shared_off
    move.w %d5,(%a2)
    bra.s .owned_done
.owned_shared_off:
    move.w #-1,(%a2)
    bra.s .owned_done
.owned_next:
    lea 256(%a3),%a3
    subq.l #1,%d0
    bne.s .owned_scan
.owned_call:
    clr.l -(%sp)
    move.l %d4,-(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    /* Both paths return to this exact PC, the slot hooks' provenance. */
    bsr.w .owned_stock
mh_key_owned_return:
    lea 16(%sp),%sp
.owned_done:
    movem.l (%sp),%d2-%d5/%a2-%a3
    lea 24(%sp),%sp
    rts
.owned_stock:
    lea -28(%sp),%sp
    movem.l %d2-%d7/%a2,(%sp)
    tst.l %d4
    bne.s .owned_stock_on
    /* Release the captured token even if the current Part says CHAN OFF.
     * Stock's recorder is disabled here; physical roots record separately. */
    move.l %d2,%d5
    moveq #0,%d6
    moveq #0,%d7
    jmp 0x4009eafa
.owned_stock_on:
    jmp 0x4009e9b0

/* Stock computes (pitch+2048)*2; bias the private base accordingly.
 * d5 has gained arp flag bits at the arp store, hence the low-three mask.
 * The on/arp stores still have two stock call arguments on their stack. */
mh_key_slot_on:
    pea 0x4009eaba
    bra.s .slot_args
mh_key_slot_arp:
    pea 0x4009eaf0
.slot_args:
    move.l %d0,-(%sp)
    move.l 44(%sp),%d0
    bra.s .slot_choose
mh_key_slot_off:
    pea 0x4009eb08
    bra.s .slot_noargs
mh_key_slot_clear:
    pea 0x4009eb74
.slot_noargs:
    move.l %d0,-(%sp)
    move.l 36(%sp),%d0
.slot_choose:
    lea 0x46c78d70,%a0
    cmpi.l #mh_key_owned_return,%d0
    bne.s .slot_done
    lea mh_key_tokens-4096,%a0
    move.l %d5,%d0
    andi.l #7,%d0
    lsl.l #8,%d0
    adda.l %d0,%a0
.slot_done:
    move.l (%sp)+,%d0
    rts
/* d0 track, d1 pitch: an existing bypass key becomes a shared chord tone. */
mh_adopt_key:
    lea mh_key_tokens,%a0
    lsl.l #8,%d0
    adda.l %d0,%a0
    lea 0x46c79d70,%a1
    move.w (%a1,%d1.l*2),%d0
    move.w %d0,(%a0,%d1.l*2)
    moveq #-1,%d0
    move.w %d0,(%a1,%d1.l*2)
    rts
    .balign 4
mh_key_tokens: .space 2048,255
