| Generated control.s appends this adapter to the freestanding C engine.
| All stock scene/LFO writes have finished; publish into the outgoing frame.
        .text
        .balign 4
        .global eu_frame_hook, eu_seq_start, eu_seq_resume
eu_frame_hook:
        lea     -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        jsr     eu_publish_frame
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea     16(%sp),%sp
        lea     0x800000f0,%a1     | displaced, next MOVE sets the flags
        jmp     0x4000d568

| A fresh PLAY resets all instances together at the same anchor the stock
| transport sets for its first tick.
        .global eu_seq_start,eu_seq_resume
eu_seq_start:
eu_seq_resume:

| The whole SR is saved after the call has pushed its return address (BSR,
| LEA and MOVEM leave the CCR of the displaced PLAYING store alone), the
| interrupt mask is raised to 7 around eu_clock_start, and the saved SR
| restores both the mask and that CCR.
eu_reset_clock:
        lea     -28(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,%sp@(12)
        move.w  %sr,%d1
        move.w  %d1,%sp@(8)
        move.w  #0x2700,%sr         | the frame ISR reads eu_clock
        move.l  #eu_clock,(%sp)
        move.l  0x4610757c,%d0
        move.l  %d0,4(%sp)
        jsr     eu_clock_start
        move.w  %sp@(8),%d1
        move.w  %d1,%sr
        movem.l %sp@(12),%d0-%d1/%a0-%a1
        lea     28(%sp),%sp
        rts

| Explicitly initialized, loader-owned DRAM, not uninitialized BSS. The
| C's static assertions check these sizes on both target and host compilers.
        .balign 4
        .global eu_clock, eu_states
eu_clock:
        .zero   20
eu_states:
        .zero   2624
