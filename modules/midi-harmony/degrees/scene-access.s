/* Adapter to upstream MIDI SCENES public slot API. */
    .include "remix.inc"
    .text
    .global hd_scene_memory_c,hd_scene_ensure_c,hd_scene_invalidate_c,hd_scene_changed_c
hd_scene_memory_c:
.if HD_SCENES
    move.l #scn_lib,%d0
.else
    moveq #0,%d0
.endif
    rts
hd_scene_ensure_c:
.if HD_SCENES
    moveq #0,%d0
    moveq #0,%d1
    jmp scn_slot_ptr
.else
    rts
.endif
hd_scene_invalidate_c:
.if HD_SCENES
    jmp scn_invalidate
.else
    rts
.endif
hd_scene_changed_c:
.if HD_SCENES
    move.l 4(%sp),%d0
    jmp scn_slot_changed
.else
    rts
.endif

    .macro HOLD symbol,side
    .global \symbol
\symbol:
    jsr 0x4006dbcc
.if HD_SCENES
    tst.l %d0
    bne.s 1f
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d6,-(%sp)
    move.l %d3,-(%sp)
    pea \side
    jsr hd_scene_delta_c
    lea 12(%sp),%sp
    move.l %d0,%d6
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    cmpi.l #0x80000000,%d6
    bne.s 1f
    moveq #1,%d0 /* skip dormant NOT2-4 in HARM, using native guard result */
1:
.endif
    rts
    .endm
    HOLD hd_scene_hold_a,0
    HOLD hd_scene_hold_b,1
