| Original P2NV writer from upstream 063a4262, unchanged instructions.
| Standalone synthetic table; no Elektron bytes. Upgrade-compatibility oracle.
.set NV, 0x100f8600
.set NV_END, 0x100ffe00
.set NV_MAX, (NV_END-NV-16)/3
.set NV_MAGIC, 0x50324e56
.set BANK_B, 98304
.text
.globl nv_save, STORE, NVBANK
nv_save:
        lea     %sp@(-40),%sp
        movem.l %d0-%d5/%a0-%a1,%sp@
        move.w  %sr,%d1
        move.w  %d1,%sp@(36)           | the caller's SR
        move.w  #0x2700,%sr
        movel   %d0,NVBANK
        addql   #1,NVGEN
        movel   NVGEN,%d1
        movel   %d1,%sp@(32)           | this save's ticket
        move.w  %sp@(36),%d1
        move.w  %d1,%sr
ns_again:
        movel   NVBANK,%d0
        lea     NV,%a1
        clrl    %a1@                   | no magic while it is written
        movel   %d0,%a1@(4)
        bsr.w   bank_at                | a0 = the bank's page 2
        lea     %a1@(16),%a1
        moveq   #0,%d2                 | count
        moveq   #0,%d3                 | sum
        moveq   #0,%d4                 | index
ns_loop:
        movel   %sp@(32),%d1
        cmpl    NVGEN,%d1
        bne.w   ns_again               | a newer save started meanwhile
        cmpil   #BANK_B,%d4
        bcc.s   ns_done
        movel   %a0@(0,%d4:l),%d0      | four at a time past the empty ones
        moveq   #-1,%d1
        cmpl    %d1,%d0
        bne.s   ns_byte
        addql   #4,%d4
        bra.s   ns_loop
ns_byte:
        moveq   #3,%d5
ns_b4:  moveq   #0,%d0
        moveb   %a0@(0,%d4:l),%d0
        cmpil   #0xff,%d0
        beq.s   ns_next
        cmpil   #0x7f,%d0
        bhi.s   ns_fail                | not a knob value: no copy
        cmpil   #NV_MAX,%d2
        bcc.s   ns_fail                | does not fit: no copy
        movel   %d4,%d1
        lsll    #7,%d1
        orl     %d0,%d1                | the entry
        addl    %d1,%d3
        moveb   %d1,%a1@(2)
        lsrl    #8,%d1
        moveb   %d1,%a1@(1)
        lsrl    #8,%d1
        moveb   %d1,%a1@
        addql   #3,%a1
        addql   #1,%d2
ns_next:
        addql   #1,%d4
        subql   #1,%d5
        bpl.s   ns_b4
        bra.s   ns_loop
ns_fail:
        moveq   #-1,%d2                | commit nothing, magic stays clear
ns_done:
        move.w  #0x2700,%sr
        movel   %sp@(32),%d1
        cmpl    NVGEN,%d1
        beq.s   ns_commit
        move.w  %sp@(36),%d1           | a newer save started: unmask, start over
        move.w  %d1,%sr
        bra.w   ns_again
ns_commit:
        tstl    %d2
        bmi.s   ns_end
        lea     NV,%a1
        movel   %d2,%a1@(8)
        movel   %d3,%a1@(12)
        movel   #NV_MAGIC,%d0
        movel   %d0,%a1@
ns_end: move.w  %sp@(36),%d1
        move.w  %d1,%sr
        movem.l %sp@,%d0-%d5/%a0-%a1
        lea     %sp@(40),%sp
        rts

bank_at:
        movel   #BANK_B,%d1
        mulu.l  %d1,%d0
        addil   #STORE,%d0
        moveal  %d0,%a0
        rts

.bss
.align 4
STORE: .space 16*BANK_B
NVBANK: .space 4
NVGEN: .space 4
