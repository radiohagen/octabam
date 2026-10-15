/* Native Part settings. UI getters/setters use the selected working Part;
 * explicit getters take d0 track,d1 context and preserve everything but d0.
 * Playback uses mh_active or explicit getters, never the UI context.
 * Offset 16: VOIC[2:0], SPRD[4:3], ROOT[6:5].
 * Offset 18: CHRD[2:0], SIZE[4:3] (NAT/2/3/4). */
    .include "remix.inc"
    .text
    .macro SETTING prefix,field,shift,mask,maximum
    .global \prefix\()_get,\prefix\()_get_at,\prefix\()_set
\prefix\()_get:
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr mp_ui_context
    move.l %d0,%d1
    move.l (%sp)+,%d0
    bsr.w \prefix\()_get_at
    move.l (%sp)+,%d1
    tst.l %d0
    rts
\prefix\()_get_at:
    move.l %d2,-(%sp)
    moveq #\field,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .L\prefix\()_default
    .if \field==18
    cmpi.l #31,%d0
    bhi.s .L\prefix\()_default
    .endif
    .ifc \prefix,mh
    cmpi.l #2,%d0
    bhi.s .L\prefix\()_default
    .endif
    .if \shift
    lsr.l #\shift,%d0
    .endif
    andi.l #\mask,%d0
    cmpi.l #\maximum,%d0
    bls.s .L\prefix\()_read_done
.L\prefix\()_default:
    moveq #0,%d0
.L\prefix\()_read_done:
    move.l (%sp)+,%d2
    tst.l %d0
    rts
\prefix\()_set:
    .ifc \prefix,mh
    jmp hd_set
    .global mh_set_native
mh_set_native:
    .endif
    lea -24(%sp),%sp
    movem.l %d1-%d5/%a0,(%sp)
    cmpi.l #7,%d0
    bhi.w .L\prefix\()_write_bad
    cmpi.l #\maximum,%d1
    bhi.w .L\prefix\()_write_bad
    move.l %d0,%d4
    move.l %d1,%d5
    jsr mp_ui_context
    move.l %d0,%d1
    move.l %d4,%d0
    moveq #\field,%d2
    jsr mp_read
    tst.l %d0
    bmi.s .L\prefix\()_write_bad
    .if \field==18
    cmpi.l #31,%d0
    bls.s .L\prefix\()_packed_valid
    moveq #0,%d0
.L\prefix\()_packed_valid:
    .endif
    .ifc \prefix,mh
    moveq #0,%d0
    .else
    andi.l #(127-(\mask<<\shift)),%d0
    .endif
    .if \shift
    lsl.l #\shift,%d5
    .endif
    or.l %d5,%d0
    move.l %d0,%d3
    move.l %d4,%d0
    jsr mp_write
    tst.l %d0
    beq.s .L\prefix\()_write_done
    /* Only reset the sounding context's history, not another Part's. */
    move.l %d4,%d0
    jsr mp_play_context
    cmp.l %d1,%d0
    bne.s .L\prefix\()_write_ok
    lea mh_voice_history,%a0
    lsl.l #3,%d4
    clr.l 4(%a0,%d4.l)
.L\prefix\()_write_ok:
    moveq #1,%d0
    bra.s .L\prefix\()_write_done
.L\prefix\()_write_bad:
    moveq #0,%d0
.L\prefix\()_write_done:
    movem.l (%sp),%d1-%d5/%a0
    lea 24(%sp),%sp
    rts
    .endm
    SETTING mh,5,0,3,2
    SETTING mh_voic,16,0,7,4
    SETTING mh_sprd,16,3,3,2
    SETTING mh_root,16,5,3,3
    SETTING mh_size,18,3,3,3

    .global mh_omit_get,mh_omit_set
mh_omit_get:
    bsr.w mh_root_get
    cmpi.l #1,%d0
    bls.s .omit_done
    moveq #0,%d0
.omit_done:
    rts
mh_omit_set:
    cmpi.l #1,%d1
    bhi.s .omit_done
    bra.w mh_root_set
