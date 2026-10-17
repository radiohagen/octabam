    .include "remix.inc"
    .text
    .global hd_memcpy,hd_step_copy,hd_step_apply
/* Native memcpy ABI, with source identity captured before any aliasing write. */
hd_memcpy:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l 24(%sp),-(%sp)
    move.l 24(%sp),-(%sp)
    move.l 24(%sp),-(%sp)
    jsr hd_copy_before_c
    /* Reload arguments: callees own their incoming argument slots. */
    move.l 28(%sp),(%sp)
    move.l 32(%sp),4(%sp)
    move.l 36(%sp),8(%sp)
    /* The bridge lets P2 copy its own mirror before the one native copy. */
    .ifdef HAVE_PLOCKS_BRIDGE
    jsr plk_memcpy
    .else
    jsr 0x40020898
    .endif
    lea 12(%sp),%sp
    move.l %d0,-(%sp)
    jsr hd_copy_after_c
    tst.l %d0
    bmi.s .copy_done
    moveq #0,%d1
    move.b 0x80000002,%d1
    cmp.l %d1,%d0
    bne.s .copy_done
    jsr ch_nv_save
.copy_done:
    move.l (%sp)+,%d0
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
hd_step_copy: /* ordinary five-argument step-copy ABI, all registers kept */
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l 40(%sp),-(%sp) /* extra return address from ch_step_copy */
    move.l 40(%sp),-(%sp)
    move.l 40(%sp),-(%sp)
    move.l 40(%sp),-(%sp)
    move.l 40(%sp),-(%sp)
    jsr hd_step_copy_c
    lea 20(%sp),%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* After the native 32-byte root/lock record has reached bank and CS1. */
hd_step_apply:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d4,-(%sp)
    move.l 120(%sp),-(%sp) /* original sp+100 track */
    move.l 120(%sp),-(%sp) /* original sp+96 pattern */
    move.l %d3,-(%sp)
    move.l %a5,-(%sp)
    jsr hd_step_paste_c
    lea 20(%sp),%sp
    tst.l %d0
    bmi.s .step_done
    moveq #0,%d1
    move.b 0x80000002,%d1
    cmp.l %d1,%d0
    bne.s .step_done
    jsr ch_nv_save
.step_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    move.b #1,%d0
    lsl.l %d3,%d0
    jmp 0x4002c772
