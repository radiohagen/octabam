| Complete the first PIO sector's bookkeeping before restoring interrupts.
| Stock has already saved d2/d3 on the stack. d3 holds the caller's SR
| (the poke at 0x40014cf2 retains it instead of restoring it early).
| No state, no DSP, no change to the bytes sent to the card.
        .text
        .globl ata_write_return
ata_write_return:
        move.w  %d3,%sr
        move.l  %d2,%d0
        move.l  (%sp)+,%d2
        move.l  (%sp)+,%d3
        rts
