| REC THRESHOLD -- recorder TRIG value 3 (THR): TRACK + REC on an idle
| recorder arms it, and the recording starts on the first frame whose
| input level crosses the track's LEV.
|
| Hooks, in both recorder key handlers (0x40083544, and 0x400836d8, which
| TRACK + REC reaches; the _trk entries):
|   idle_gate   (0x4008364e; idle_gate_trk 0x40083836) the recorder key handler's idle branch (voice
|               byte 1 == 0), where stock posts its start through
|               0x40005178(track, (keys + 0x8000) | 0x10, 1) without reading
|               TRIG. Under THR that start word goes into `armed[track]`
|               instead; a second press while armed cancels.
|   trig_gate   (0x400835e2; trig_gate_trk 0x400837b6) the TRIG decode, reached only while
|               the recorder runs (voice byte 1 != 0): THR behaves as ONE2
|               (the same keys again stop with 0x80). Without it a value
|               of 3 falls to HOLD, whose key release stops the take.
|   frame_check (0x4000ab72) the frame interrupt, where it advances the
|               input page index. Only while some track is armed: the
|               page before the new index (all four inputs, 16 samples
|               each, 64 longs), the newest one filled, is compared with
|               +/-THRESH; on a crossing
|               every armed track's word moves into the immediate mailbox
|               0x46c7e9fa[track], which the dispatcher at 0x4000d2a0 acts
|               on later in the same interrupt.
|
| Measured under the port (stock image, empty project, 11 Oct 2026): TRACK 1
| + REC AB on an idle recorder posts 0x9010 at 0x400051f4 and the take
| arms (LIMIT written at 0x400069d6, voice byte 1 -> 0xff); a second press
| posts 0x1010 and re-arms. 0x9010 written straight into the mailbox of an
| idle recorder arms it; 0x80 and 0x1040 are consumed and arm nothing.
| Here, just after the index advances, the page it names is the one eDMA
| fills during the coming frame and still holds the samples of 8 frames
| ago: scanning it detected a numbered input 120 samples late (port, 11 Oct
| 2026). STEM REC reads that page later in the frame, complete (STEM_REC.md
| 18.7). A start posted here waits 5 frames (record +16 counts 80 -> 0) and
| the recorder reads 5 pages back (record +20 = 80, 0x400075a4), so the
| take begins at the detection frame. Not measured on a unit.
| The armed start is immediate, so QREC is not applied, and under THR its
| byte is the track's LEV instead: -60 .. 0 dB (raw -1 .. 16 through
| lev_db: 4 dB steps to -8, then 2 dB), stored with the Part. Setting TRIG
| to THR on a track whose QREC byte is OFF (raw -1, never set) makes it
| -40 dB (raw 4; trig_init).
| RECORDING SETUP 2 draws it as LEV in QREC's cell, and the live input
| level as IN in QPL's (draw_gate), and QPL is not edited while TRIG is
| THR (edit_gate). The meter runs only while the page draws (meter_cnt).
        .text
        .global idle_gate
        .global trig_gate
        .global idle_gate_trk
        .global trig_gate_trk
        .global frame_check
        .global trig_screen
        .global draw_gate
        .global edit_gate
        .global trig_init
        .global blink_gate

        .equ    TRIG_THRESH, 3          | the new TRIG value
        .equ    METER_HOLD, 1400        | frames (~0.5 s) the meter runs after a draw
        .equ    HOLD_FRAMES, 1400       | frames (~0.5 s) IN holds a peak before it falls
        .equ    LEV_INIT, 4             | QREC raw for -40 dB (lev_db), set when TRIG becomes THR
        .equ    BLINK_BIT, 10           | frame counter bit: 1,024 frames (~0.37 s) on, then off
        .equ    ICON_CACHE, 0x400c0cb8  | the track status icons' drawn states, [track*4]
        .equ    MAILBOX, 0x46c7e9fa     | immediate recorder command words, [track*4]
        .equ    VOICES, 0x800049d8      | per-track voice records, 168 B; byte 1 = recorder running
        .equ    PAGE_INDEX, 0x46104d00
        .equ    PAGES, 0x80005660       | 8 input pages of 0x100 bytes, on-chip SRAM

| 0x4008364e displaced: moveq #1,%d0 / cmpl %d6,%d0 / bnes 0x400836ce.
| Reached with d2 != 0 (a REC key held). d0, d1 and a0 are scratch in the
| handler (it saves d2-d7 only).
idle_gate:
        moveq   #1,%d0
        cmp.l   %d6,%d0
        bne.s   .ig_done                | key release: nothing, as stock
        moveq   #TRIG_THRESH,%d0
        cmp.l   %d5,%d0
        beq.s   .ig_thresh
        jmp     (0x40083654).l          | any other TRIG: stock's start
.ig_thresh:
        moveq   #7,%d0
        cmp.l   %d4,%d0
        bcs.s   .ig_done                | track out of range
        move.l  %d4,%d1
        lsl.l   #2,%d1
        lea     armed,%a0
        adda.l  %d1,%a0
        tst.l   (%a0)
        beq.s   .ig_arm
        clr.l   (%a0)                   | armed: a press cancels
        bra.s   .ig_done
.ig_arm:
        move.l  %d4,%d1
        bsr     track_level
        move.l  %d0,32(%a0)             | armed_thr[track], before the word
        move.l  %d2,%d0
        addi.l  #0x8000,%d0
        moveq   #0x10,%d1
        or.l    %d1,%d0
        move.l  %d0,(%a0)               | stock's start word, held until the threshold
.ig_done:
        jmp     (0x400836ce).l          | the handler's epilogue

| 0x400835e2 displaced: moveq #1,%d0 / cmpl %d5,%d0 / bnes 0x40083622.
trig_gate:
        moveq   #1,%d0
        cmp.l   %d5,%d0
        beq.s   .tg_one2
        moveq   #TRIG_THRESH,%d0
        cmp.l   %d5,%d0
        beq.s   .tg_thr
        jmp     (0x40083622).l          | 2 (HOLD) and anything else, as stock
.tg_thr:
        moveq   #1,%d0
.tg_one2:
        jmp     (0x400835e8).l          | ONE2's path, with d0 = 1 as stock leaves it

| The TRACK + REC handler 0x400836d8 (a loop over the held tracks, d4 the
| track, d6 TRIG, d3 REC keys << 12, d5 the recorder's current keys, a3
| 1 = press; 5178 called through a4) has the same two branches.
|
| 0x40083836 displaced: moveq #1,%d0 / cmpl %a3,%d0 / bnes 0x400838b0 (the
| idle branch, reached with d2 and d3 set; 0x400838b0 is the next track).
| Stock's start word for the idle branch is at 56(sp), built at 0x40083904.
idle_gate_trk:
        moveq   #1,%d0
        cmp.l   %a3,%d0
        bne.s   .it_next                | key release: nothing, as stock
        moveq   #TRIG_THRESH,%d0
        cmp.l   %d6,%d0
        beq.s   .it_thresh
        jmp     (0x4008383c).l          | any other TRIG: stock's start
.it_thresh:
        moveq   #7,%d0
        cmp.l   %d4,%d0
        bcs.s   .it_next
        move.l  %d4,%d1
        lsl.l   #2,%d1
        lea     armed,%a0
        adda.l  %d1,%a0
        tst.l   (%a0)
        beq.s   .it_arm
        clr.l   (%a0)                   | armed: a press cancels
        bra.s   .it_next
.it_arm:
        move.l  %d4,%d1
        bsr     track_level
        move.l  %d0,32(%a0)             | armed_thr[track], before the word
        move.l  56(%sp),(%a0)           | stock's start word, held until the threshold
.it_next:
        jmp     (0x400838b0).l          | the next track

| 0x400837b6 displaced: moveq #1,%d1 / cmpl %d6,%d1 / bnes 0x400837ea (the
| running branch's ONE2 test). THR takes ONE2's path; d1 = 1 is read there.
trig_gate_trk:
        moveq   #1,%d1
        cmp.l   %d6,%d1
        beq.s   .tt_one2
        moveq   #TRIG_THRESH,%d1
        cmp.l   %d6,%d1
        beq.s   .tt_thr
        jmp     (0x400837ea).l          | 0 and 2 (HOLD), as stock
.tt_thr:
        moveq   #1,%d1
.tt_one2:
        jmp     (0x400837bc).l

| 0x4000ab72 displaced: movel %d0,0x46104d00. d0 = the new page index and
| must survive; every register used here is saved. Runs only while a track
| is armed or the meter is wanted: the newest complete page's peak |sample|
| feeds the meter and is compared with each armed track's level. A track
| at or over its level fires only if its TRIG is still THR (it may have
| been edited, or the Part changed) and its recorder is idle (voice byte 1
| clear: no take started by another route); either way the arm is spent.
frame_check:
        move.l  %d0,(PAGE_INDEX).l      | displaced
        lea     -24(%sp),%sp
        movem.l %d0-%d3/%a0-%a1,(%sp)
        lea     armed,%a0
        move.l  (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (%a0)+,%d1
        or.l    (meter_cnt).l,%d1
        beq.w   .fc_out                 | nothing armed, no meter: done
        addq.l  #1,(blink).l            | the armed icons' blink clock
        addq.l  #7,%d0                  | the page before the new index: (index - 1) & 7,
        moveq   #7,%d1                  | the newest one filled (the new one fills this frame)
        and.l   %d1,%d0
        lsl.l   #8,%d0
        addi.l  #PAGES,%d0
        movea.l %d0,%a0
        moveq   #0,%d2                  | the peak |sample|
        moveq   #63,%d1                 | 64 longs: C, D, A, B x 16 samples
.fc_scan:
        move.l  (%a0)+,%d0
        bpl.s   .fc_pos
        neg.l   %d0
.fc_pos:
        cmp.l   %d2,%d0
        bls.s   .fc_less
        move.l  %d0,%d2
.fc_less:
        subq.l  #1,%d1
        bpl.s   .fc_scan
        move.l  (meter_cnt).l,%d0
        beq.s   .fc_arm
        subq.l  #1,%d0
        move.l  %d0,(meter_cnt).l
        move.l  (in_peak).l,%d0         | the meter: a louder page takes over and
        cmp.l   %d2,%d0                 | restarts the hold; else the hold counts
        bhi.s   .fc_quieter             | down, then the level falls ~29 dB/s
        move.l  %d2,(in_peak).l
        move.l  #HOLD_FRAMES,%d0
        move.l  %d0,(in_hold).l
        bra.s   .fc_arm
.fc_quieter:
        move.l  (in_hold).l,%d1
        beq.s   .fc_fall
        subq.l  #1,%d1
        move.l  %d1,(in_hold).l
        bra.s   .fc_arm
.fc_fall:
        move.l  %d0,%d1                 | x -= x/1024 + x/4096 each frame (5/4096:
        moveq   #10,%d3                 | -0.0106 dB a frame at 44.1 kHz / 16,
        lsr.l   %d3,%d1                 | ~29 dB/s; -60 dB from 0 in ~2 s)
        sub.l   %d1,%d0
        lsr.l   #2,%d1
        sub.l   %d1,%d0
        move.l  %d0,(in_peak).l
.fc_arm:
        lea     armed,%a0
        moveq   #0,%d1                  | track x 4
.fc_fire:
        move.l  (%a0,%d1.l),%d0
        beq.s   .fc_next
        cmp.l   32(%a0,%d1.l),%d2       | the peak against armed_thr[track]:
        bcs.s   .fc_next                | at or over it fires (so 0 dB can)
        move.l  %d1,%d3                 | track x 4
        lsr.l   #2,%d1
        bsr     rec_addr                | a1: the track's record in the Part
        mvs.b   3(%a1),%d1
        cmpi.l  #TRIG_THRESH,%d1
        bne.s   .fc_drop                | TRIG no longer THR (edited, a Part change)
        move.l  %d3,%d1
        lsr.l   #2,%d1
        muls.w  #168,%d1
        lea     (VOICES).l,%a1
        tst.b   1(%a1,%d1.l)
        bne.s   .fc_drop                | recording already (another route): leave it
        lea     (MAILBOX).l,%a1
        move.l  %d0,(%a1,%d3.l)         | what stock's press would have stored
.fc_drop:
        clr.l   (%a0,%d3.l)             | the arm is spent either way
        move.l  %d3,%d1
.fc_next:
        addq.l  #4,%d1
        moveq   #32,%d0
        cmp.l   %d0,%d1
        bne.s   .fc_fire
.fc_out:
        movem.l (%sp),%d0-%d3/%a0-%a1
        lea     24(%sp),%sp
        jmp     (0x4000ab78).l

| d1 = track -> a1 = its recorder record in the current Part, 12 bytes:
| INAB INCD RLEN TRIG SRC3 LOOP FIN FOUT AB QREC QPL CD (as 0x40083592
| and 0x4002fd80 address it). Uses d1; keeps d0 and d2.
rec_addr:
        move.l  %d2,-(%sp)
        move.l  %d1,%d2
        lsl.l   #2,%d2                  | 4 t
        movea.l %d2,%a1
        add.l   %d2,%d2                 | 8 t
        adda.l  %d2,%a1                 | 12 t
        mvz.b   (0x100b14cf).l,%d1      | the Part
        move.l  #6322,%d2
        muls.l  %d2,%d1
        adda.l  %d1,%a1
        adda.l  (0x46c82456).l,%a1
        adda.l  #0x8f382,%a1
        move.l  (%sp)+,%d2
        rts

| d0 = a QREC byte -> d0 = LEV in dB, from lev_db (raw -1 .. 16; out of
| range: the first, -60). Uses d1, a1.
qrec_db:
        moveq   #-1,%d1
        cmp.l   %d1,%d0
        blt.s   .qd_def
        moveq   #16,%d1
        cmp.l   %d1,%d0
        ble.s   .qd_ok
.qd_def:
        moveq   #-1,%d0
.qd_ok:
        lea     lev_db+1,%a1            | raw -1 is lev_db[0]
        mvs.b   (%a1,%d0.l),%d0
        rts

| d1 = track -> d0 = its LEV as a level (db_table). Uses d1, a1; keeps a0, d2.
track_level:
        bsr     rec_addr
        mvs.b   9(%a1),%d0              | QREC's byte
        bsr     qrec_db
        moveq   #60,%d1
        add.l   %d1,%d0                 | dB + 60: the table index
        lsl.l   #2,%d0
        lea     db_table,%a1
        move.l  (%a1,%d0.l),%d0
        rts

| 0x4002fdbe displaced: movea.l %d5,%a1 / movea.l (%a1),%a0 / tst.l %a0
| (then beq.s 0x4002fdd2), in RECORDING SETUP 2's six-cell loop: d6 the
| slot, d0 its value, d3 the track, a5 its name, a2 the row, -8(fp) the
| 8-byte value buffer. d1 and a1 are dead here: the rest of the cell
| (0x4002fdc4..0x4002fe56) does not read d1, and the next write, 0x4002fe5a
| or the loop head's 0x4002fd5c, comes before any read; a1 is set by the
| displaced code. On a THR track slot 9 (QREC) is drawn LEV, its
| byte in dB, and slot 10 (QPL) IN, the meter; the name is drawn as
| 0x4002fde8..0x4002fe12 does with ours, rejoining at the value's draw.
draw_gate:
        moveq   #9,%d1
        cmp.l   %d6,%d1
        beq.s   .dg_thr
        moveq   #10,%d1
        cmp.l   %d6,%d1
        beq.s   .dg_thr
.dg_stock:
        movea.l %d5,%a1                 | displaced
        movea.l (%a1),%a0
        tst.l   %a0
        jmp     (0x4002fdc4).l
.dg_thr:
        move.l  %d0,-(%sp)
        move.l  %d3,%d1
        bsr     rec_addr
        move.l  (%sp)+,%d0
        mvs.b   3(%a1),%d1              | TRIG
        cmpi.l  #TRIG_THRESH,%d1
        bne.s   .dg_stock               | not THR: stock, with d0 as it computed
        moveq   #9,%d1
        cmp.l   %d6,%d1
        bne.s   .dg_in
        mvs.b   9(%a1),%d0              | LEV: QREC's byte, in dB
        bsr     qrec_db                 | (a1 is not needed again here)
        move.l  %d0,-(%sp)
        pea     (0x400b465d).l          | "%d"
        pea     -8(%fp)
        jsr     (0x40013a08).l
        lea     12(%sp),%sp
        lea     lbl_lev,%a0
        bra.s   .dg_name
.dg_in:
        move.l  #METER_HOLD,%d0
        move.l  %d0,(meter_cnt).l
        move.l  (in_peak).l,%d0
        lea     db_table,%a1
        moveq   #60,%d1
.dg_find:
        cmp.l   (%a1,%d1.l*4),%d0       | the loudest step the peak reaches
        bcc.s   .dg_found
        subq.l  #1,%d1
        bpl.s   .dg_find
        pea     lbl_low                 | under -60 dB
        pea     -8(%fp)
        jsr     (0x40013a08).l
        addq.l  #8,%sp
        bra.s   .dg_inname
.dg_found:
        moveq   #60,%d0
        sub.l   %d0,%d1                 | dB
        move.l  %d1,-(%sp)
        pea     (0x400b465d).l          | "%d"
        pea     -8(%fp)
        jsr     (0x40013a08).l
        lea     12(%sp),%sp
.dg_inname:
        lea     lbl_in,%a0
.dg_name:
        move.l  %a2,%d2
        addi.l  #9,%d2
        move.l  %a0,-(%sp)              | our name where stock pushes a5
        pea     (0x400b451d).l
        clr.l   -(%sp)
        pea     (1).w
        move.l  -52(%fp),-(%sp)
        move.l  %d2,-(%sp)
        move.l  %d4,-(%sp)
        pea     (0x400ba876).l
        jsr     (0x40013904).l
        lea     32(%sp),%sp
        jmp     (0x4002fe16).l          | stock draws the value from -8(fp)

| 0x4002ef60 displaced: mvz.b 0x100b14cc,%d3 (the track), in RECORDING
| SETUP's encoder editor with d4 the absolute slot. On a THR track slot 10
| shows IN, so QPL is not edited: out through stock's epilogue, before any
| store.
edit_gate:
        mvz.b   (0x100b14cc).l,%d3      | displaced
        moveq   #10,%d0
        cmp.l   %d4,%d0
        bne.s   .eg_stock
        move.l  %d3,%d1
        bsr     rec_addr
        mvs.b   3(%a1),%d0              | TRIG
        moveq   #TRIG_THRESH,%d1
        cmp.l   %d0,%d1
        bne.s   .eg_stock
        jmp     (0x4002f0ce).l
.eg_stock:
        jmp     (0x4002ef66).l

| 0x4002fb8e, a "jsr" detour: RECORDING SETUP's push of the stock TRIG
| formatter 0x4002f1d4 (`move.l d4,(sp); pea pc(0x4002f1d4)`), replayed
| with trig_fmt pushed instead. d0 is dead at the site (0x4002fba4).
trig_screen:
        move.l  (%sp)+,%d0              | the return address
        move.l  %d4,(%sp)               | displaced
        pea     trig_fmt                | in place of the stock formatter
        move.l  %d0,-(%sp)
        rts

| fmt(buf, value): 3 -> "THR"; 0..2 the stock formatter (ONE, ONE2, HOLD;
| stock prints HOLD for anything above 2).
trig_fmt:
        moveq   #TRIG_THRESH,%d0
        cmp.l   8(%sp),%d0
        bne.s   .tf_stock
        lea     thr_label,%a0
        move.l  %a0,8(%sp)
        jmp     (0x40013a08).l          | sprintf(buf, "THR")
.tf_stock:
        jmp     (0x4002f1d4).l

thr_label:
        .asciz  "THR"

| 0x4002f0b4 displaced: mvz.b 0x100b14cc,%d0, in the setup editor once the
| Part (0x4002f03a), its SRAM mirror (0x4002f042) and the dirty flags are
| written; d4 the absolute slot, d6 the byte stored. TRIG (slot 3) just set
| to THR on a track whose QREC byte is OFF (raw -1, never set): LEV := -40
| dB in the same three places stock writes a value, the Part, the mirror
| (0x100a54d0 + part x 6322 + track x 12) and the published copy
| (0x80000c94 + track x 12, as 0x4002f0ca). An arm is not touched here;
| blink_gate drops it (THR7 dropped it here; its failure to record from
| inside RECORDING SETUP on the unit was GRID RECORDING, stock's rule at
| 0x400836e4, not this code).
trig_init:
        moveq   #3,%d0
        cmp.l   %d4,%d0
        bne.s   .ti_out
        mvs.b   %d6,%d1
        moveq   #TRIG_THRESH,%d0
        cmp.l   %d1,%d0
        bne.s   .ti_out
        mvz.b   (0x100b14cc).l,%d1      | the track
        bsr     rec_addr                | a1: its record in the Part
        mvs.b   9(%a1),%d1
        moveq   #-1,%d0
        cmp.l   %d1,%d0
        bne.s   .ti_out                 | LEV already set: kept
        moveq   #LEV_INIT,%d0
        move.b  %d0,9(%a1)              | the Part
        suba.l  (0x46c82456).l,%a1
        adda.l  #0x100a54d0-0x8f382,%a1
        move.b  %d0,9(%a1)              | the SRAM mirror
        mvz.b   (0x100b14cc).l,%d1
        muls.w  #12,%d1
        lea     (0x80000c94).l,%a0
        move.b  %d0,9(%a0,%d1.l)        | the published copy
.ti_out:
        mvz.b   (0x100b14cc).l,%d0      | displaced
        jmp     (0x4002f0ba).l

| LEV in dB for each QREC raw value -1 .. 16: 4 dB steps to -8, then 2 dB
| to 0; -40 (index 5, raw 4) is LEV_INIT.
lev_db:
        .byte   -60, -56, -52, -48, -44, -40, -36, -32, -28, -24
        .byte   -20, -16, -12, -8, -6, -4, -2, 0
| 0x4004bee2, a "jsr" detour: the track status icon renderer's `lea
| 0x400c0cb8,%a0`, its drawn-state cache (d3 the track, a4 the state it is
| about to compare and draw: 0..3; a Pickup takes its own path, and never
| arms). While the track is armed, every other blink phase a4 becomes
| 0x10 + a4, a state the draw switch has no glyph for: the state differs
| from the cached one, so the box is cleared (0x4004bf4a) and left empty,
| and the next phase redraws the real icon. The icon blinks whatever it
| shows. A track whose TRIG is no longer THR (edited, or another Part
| loaded, while armed) loses its arm here, at the next icon draw, and
| shows its icon as stock. d0, d1 and a1 are reloaded before any read
| (0x4004befa, 0x4004bf0a, 0x4004beee and 0x4004c07a); rec_addr keeps d2
| and a0.
blink_gate:
        moveq   #7,%d0
        cmp.l   %d3,%d0
        bcs.s   .bg_out
        move.l  %d3,%d0
        lsl.l   #2,%d0
        lea     armed,%a0
        tst.l   (%a0,%d0.l)
        beq.s   .bg_out                 | not armed: the icon as stock
        move.l  %d3,%d1
        bsr     rec_addr                | a1 (reloaded at 0x4004beee before use)
        mvs.b   3(%a1),%d1
        cmpi.l  #TRIG_THRESH,%d1
        beq.s   .bg_thr
        clr.l   (%a0,%d0.l)             | TRIG not THR: the arm goes, no blink
        bra.s   .bg_out
.bg_thr:
        move.l  (blink).l,%d0
        btst    #BLINK_BIT,%d0
        beq.s   .bg_out                 | the on phase
        move.l  %a4,%d0
        moveq   #0x10,%d1
        or.l    %d1,%d0
        movea.l %d0,%a4                 | the off phase: no glyph
.bg_out:
        lea     (ICON_CACHE).l,%a0      | displaced
        rts

lbl_lev:
        .asciz  "LEV"
lbl_in:
        .asciz  "IN"
lbl_low:
        .asciz  "---"

| dB -> the level a sample must pass, -60 .. 0 dB in 1 dB steps (index dB
| + 60): full scale 0x7fffff00 x 10^(dB/20); 24-bit samples sit in the top
| 24 bits of a long.
        .balign 4
db_table:
        .long   0x0020c400, 0x0024c400, 0x00294000, 0x002e4900, 0x0033ef00
        .long   0x003a4500, 0x00416100, 0x00495b00, 0x00524f00, 0x005c5a00
        .long   0x00679f00, 0x00744300, 0x00827300, 0x00925e00, 0x00a43a00
        .long   0x00b84400, 0x00cec000, 0x00e7fa00, 0x01044900, 0x01240b00
        .long   0x0147ae00, 0x016fa900, 0x019c8600, 0x01cedc00, 0x02075600
        .long   0x0246b400, 0x028dce00, 0x02dd9500, 0x03371800, 0x039b8700
        .long   0x040c3700, 0x048aa700, 0x05188400, 0x05b7b100, 0x066a4a00
        .long   0x0732ae00, 0x08138500, 0x090fcb00, 0x0a2ada00, 0x0b687300
        .long   0x0ccccc00, 0x0e5ca100, 0x101d3f00, 0x12149a00, 0x14496000
        .long   0x16c31000, 0x198a1300, 0x1ca7d700, 0x2026f200, 0x24134600
        .long   0x287a2600, 0x2d6a8600, 0x32f52c00, 0x392ced00, 0x4026e600
        .long   0x47facc00, 0x50c33500, 0x5a9df600, 0x65ac8b00, 0x72148100
        .long   0x7fffff00

        .data
        .balign 4
armed:  .long   0, 0, 0, 0, 0, 0, 0, 0  | per track: the pending start word, 0 = not armed
armed_thr:
        .long   0, 0, 0, 0, 0, 0, 0, 0  | per track: its level when armed (armed + 32)
meter_cnt:
        .long   0                       | frames the meter still runs
in_peak:
        .long   0                       | the meter's held peak
in_hold:
        .long   0                       | frames its hold still runs
blink:
        .long   0                       | frames counted while armed (the icon's blink)
