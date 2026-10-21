/* One owner of the native boundaries. All saved state lives on the stack.
 * Callbacks may clobber d0-d7/a0-a6, but must preserve SP and interrupt mask.
 * start/resume: d0 = native PLAYING value, after it is published.
 * midi_sent: d0 = track, d1 = native pool kind, d2 = velocity, d3 = pitch.
 * Output acceptance is not evidence that an external device received MIDI.
 */
    .text
    .global seq_start,seq_resume,seq_sent_a,seq_sent_b
    .macro SAVE
    lea -64(%sp),%sp
    movem.l %d0-%d7/%a0-%a6,(%sp)
    move.w %sr,%d1
    move.w %d1,60(%sp)
    .endm
    .macro REST
    move.w 60(%sp),%d1
    move.w %d1,%sr
    movem.l (%sp),%d0-%d7/%a0-%a6
    lea 64(%sp),%sp
    .endm
seq_start:
    move.l %d0,0x800065b8
    SAVE
    lea seq_ev_start,%a0
    bsr.w seq_fire
    REST
    jmp 0x4009c3da
seq_resume:
    move.l %d0,0x800065b8
    SAVE
    lea seq_ev_resume,%a0
    bsr.w seq_fire
    REST
    jmp 0x4009c4da
seq_sent_a:
    bsr.w seq_sent
    move.b 0x400d807c,%d1
    extb.l %d1
    jmp 0x4009fbb8
seq_sent_b:
    bsr.w seq_sent
    move.b 0x400d807c,%d0
    extb.l %d0
    jmp 0x4009fd00
seq_sent:
    SAVE
    cmpi.l #7,%d7
    bhi.s seq_sent_done
    move.l %d7,%d0
    moveq #10,%d1
    mulu.l %d7,%d1
    lea 0x46c77b1e,%a0
    move.b (%a0,%d1.l),%d1
    andi.l #255,%d1
    moveq #0,%d2
    move.b 0x400d807e,%d2
    moveq #0,%d3
    move.b 0x400d807c,%d3
    lea seq_ev_midi_sent,%a0
    bsr.w seq_fire
seq_sent_done:
    REST
    rts
/* Preserve arguments and iteration state independently of every callback. */
seq_fire:
    lea -20(%sp),%sp
    movem.l %d0-%d3/%a0,(%sp)
seq_fire_next:
    move.l 16(%sp),%a0
    move.l (%a0)+,%d0
    beq.s seq_fire_done
    move.l %a0,16(%sp)
    move.l %d0,%a1
    movem.l (%sp),%d0-%d3
    jsr (%a1)
    bra.s seq_fire_next
seq_fire_done:
    lea 20(%sp),%sp
    rts
    .balign 4
    .include "remix.inc"
