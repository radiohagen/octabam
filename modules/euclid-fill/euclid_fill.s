| euclid_fill.s -- EUCLID FILL: TRACK + PAGE opens a standalone Euclid page.
|
| With any track key held, PAGE toggles this window instead of stock's
| pattern-page / SCALE path. FUNC + PAGE (SCALE SETUP) stays stock: it
| rides the FUNC layer, not this opener.
|
| Window rows: STEPS (read-only = pattern length), PULSE, ROT — same
| names/ranges as filter EUCLID. STEPS tracks SCALE SETUP length
| (NORMAL: +0x8e53; PER TRACK: first target track's TRAC+0x50). Encoder A
| = PULSE, B = ROT; UP/DOWN / LEFT/RIGHT / LEVEL edit the focused row.
| YES writes Euclidean sample trigs on the tracks held when the window
| opened (or the current track if none). NO / TRACK+PAGE / PAGE closes.
|
| Trig write: mask 0 of each target TRAC in the bank blob and its battery
| mirror at 0x1001614e, then dirty + 0x40027e00 (erase-empty's recipe).

        .set    HELD,      0x460fab40   | held track keys, bit t
        .set    UI_TRACK,  0x100b14cc
        .set    UI_PTN,    0x100b14d0
        .set    DBPTR,     0x46c82456
        .set    MIRROR,    0x1001614e
        .set    DIRTY_G,   0x100f8598
        .set    DIRTY_OFF, 0x9b332
        .set    NOTIFY,    0x40027e00
        .set    TOAST,     0x4005a2b8
        .set    PTN_STR,   0x8ed8
        .set    TRK_STR,   0x91a
        .set    PAT_LEN,   0x8e53       | pattern length (NORMAL scale)
        .set    PAT_PER,   0x8e55       | nonzero = PER TRACK
        .set    TRK_LEN,   0x50         | track length inside TRAC

        .set    WCREATE,   0x4005829c
        .set    WFRAME,    0x40056f4c
        .set    WDESTROY,  0x40055db4
        .set    CLEAR,     0x40035624
        .set    FONT,      0x400ba876   | small UI font, 6 px (tuner.s)
        .set    TEXT,      0x40012bd8   | (font, surf, x, y, limit, str)
        .set    TWIDTH,    0x40012f30   | (font, limit, str) -> pixels
        .set    RULE,      0x40011910   | (surf, x, y, x2, 1)
        .set    BOX,       0x40012254   | (surf, x1, y1, x2, y2, mode)
        .set    SPRINTF,   0x40013a08
        .set    LPUSH,     0x40031494
        .set    LPOP,      0x4003146c
        .set    SCRDIRTY,  0x46c7c72c

        .set    PAGE_GO,   0x4004ffcc   | after the displaced 8-byte prologue
        | Compact TEMPO-class box. y counts UP from the bottom.
        .set    WINW,      92
        .set    WINH,      54
        .set    Y_TITLE,   42          | WINH-12
        .set    Y_RULE,    39
        .set    Y_ROW0,    30          | STEPS
        .set    Y_ROW1,    22          | PULSE
        .set    Y_ROW2,    14          | ROT
        .set    Y_PAT,     4
        .set    PAT_H,     5
        .set    X_LAB,     10          | label column (">" sits at 3)
        .set    X_VAL,     88          | value right edge (WINW-4)

        .text
        .globl  ef_page, ef_open, ef_close, ef_draw, ef_fill
        .globl  ef_yes, ef_no, ef_up, ef_down, ef_left, ef_right, ef_level, ef_enc

| ---- 0x4004ffc4: PAGE press/release. Track held -> toggle Euclid. --------
| Displaced prologue: lea -16(sp),sp ; movem.l d2-d4/a2,(sp).
| On entry the stack is still stock's (keycode @4, event @8).
ef_page:
        tstl    ef_win
        bne.s   1f                      | open: any PAGE press closes
        tstl    HELD
        beq.s   9f                      | no track held: stock PAGE
1:      moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   8f                      | press only
        tstl    ef_win
        bne.w   ef_close
        bra.w   ef_open
8:      rts
9:      lea     -16(%sp),%sp            | displaced prologue
        movem.l %d2-%d4/%a2,(%sp)
        jmp     PAGE_GO

| ---- open / close -------------------------------------------------------
ef_open:
        movel   HELD,%d0
        bne.s   1f
        moveq   #0,%d0
        moveb   UI_TRACK,%d0
        andil   #7,%d0
        moveq   #1,%d1
        lsll    %d0,%d1
        movel   %d1,%d0
1:      movel   %d0,ef_targets
        bsr.w   ef_sync_len             | STEPS := pattern / track length
        pea     ef_close
        pea     5                       | TEMPO class: mutual eviction
        clrl    %sp@-
        clrl    %sp@-
        pea     WINH
        pea     WINW
        jsr     WCREATE
        lea     %sp@(24),%sp
        movel   %d0,ef_win
        beq.s   9f
        movel   %d0,%sp@-
        jsr     WFRAME
        addql   #4,%sp
        pea     EF_LAYER
        jsr     LPUSH
        addql   #4,%sp
        clrl    ef_cursor
        bra.w   ef_draw
9:      rts

| STEPS from the UI pattern's length (NORMAL: +0x8e53; PER TRACK: first
| target track's TRAC+0x50). Same sources as RLEN PLEN / DIRECT JUMP.
| Offsets past ±32K use an address register + add (ColdFire d16 limit).
ef_sync_len:
        moveal  DBPTR,%a0
        moveq   #0,%d0
        moveb   UI_PTN,%d0
        movel   #PTN_STR,%d1
        mulu.l  %d1,%d0
        addal   %d0,%a0                 | a0 = pattern base
        movel   %a0,%d1
        addil   #PAT_PER,%d1
        moveal  %d1,%a1
        tst.b   %a1@
        beq.s   sl_pat
        moveq   #0,%d2                  | first set bit in ef_targets
        movel   ef_targets,%d3
sl_bit: btst    %d2,%d3
        bne.s   sl_trk
        addql   #1,%d2
        moveq   #8,%d0
        cmpl    %d0,%d2
        bcs.s   sl_bit
        moveq   #0,%d2
        moveb   UI_TRACK,%d2
        andil   #7,%d2
sl_trk: movel   %d2,%d0
        movel   #TRK_STR,%d1
        mulu.l  %d1,%d0
        addil   #TRK_LEN,%d0
        moveb   %a0@(0,%d0:l),%d0
        extb.l  %d0
        bra.s   sl_clamp
sl_pat: movel   %a0,%d1
        addil   #PAT_LEN,%d1
        moveal  %d1,%a1
        moveb   %a1@,%d0
        extb.l  %d0
sl_clamp:
        moveq   #1,%d1
        cmpl    %d1,%d0
        bge.s   sl1
        moveq   #1,%d0
sl1:    moveq   #64,%d1
        cmpl    %d1,%d0
        ble.s   sl2
        moveq   #64,%d0
sl2:    movel   %d0,ef_steps
        movel   ef_pulses,%d1
        cmpl    %d0,%d1
        ble.s   sl3
        movel   %d0,ef_pulses
sl3:    movel   ef_rot,%d1
        subql   #1,%d0
        cmpl    %d0,%d1
        ble.s   sl4
        movel   %d0,ef_rot
sl4:    rts

ef_close:
        tstl    ef_win
        beq.s   9f
        pea     ef_win
        jsr     WDESTROY
        addql   #4,%sp
        pea     EF_LAYER
        jsr     LPOP
        addql   #4,%sp
9:      rts

ef_no:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        bra.w   ef_close
9:      rts

ef_yes:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        bsr.w   ef_fill
        pea     0x30
        pea     T_FILLED
        jsr     TOAST
        addql   #8,%sp
        bra.w   ef_draw
9:      rts

| ---- cursor / values (cursor 0=PULSE, 1=ROT; STEPS is pattern len) ------
ef_up:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        tstl    ef_cursor
        beq.s   8f
        subql   #1,ef_cursor
        bra.w   ef_draw
8:      moveq   #1,%d0
        movel   %d0,ef_cursor
        bra.w   ef_draw
9:      rts

ef_down:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        movel   ef_cursor,%d0
        eoril   #1,%d0                  | toggle 0 <-> 1
        movel   %d0,ef_cursor
        bra.w   ef_draw
9:      rts

ef_left:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        moveq   #-1,%d0
        bra.w   ef_nudge
9:      rts

ef_right:
        moveq   #1,%d0
        cmpl    8(%sp),%d0
        bne.s   9f
        moveq   #1,%d0
        bra.w   ef_nudge
9:      rts

| Encoder A/B: (index @4, delta @8). A -> PULSE, B -> ROT; focus follows.
ef_enc:
        movel   4(%sp),%d1              | encoder index
        moveq   #1,%d0
        cmpl    %d0,%d1
        bhi.s   9f                      | C-F: ignore
        movel   %d1,ef_cursor           | 0=PULSE, 1=ROT
        movel   8(%sp),%d0
        beq.s   9f
        bra.w   ef_nudge
9:      rts

| LEVEL encoder: (index @4, delta @8) — same ABI as TEMPO BUS / stock
| TLEVEL. Use the full signed long (panel coalesces unread detents past ±127).
ef_level:
        movel   8(%sp),%d0
        beq.w   ef_nudge_rts
        bra.w   ef_nudge
| LEFT/RIGHT enter with d0 = ±1 already. Edits PULSE or ROT only.
| ef_sync_len clobbers d0-d3/a0/a1 — park the signed delta on the stack
| first. Without that, L/R become the track index (dead on T1) and every
| encoder turn nudges upward only.
ef_nudge:
        movel   %d0,-(%sp)              | park signed delta
        bsr.w   ef_sync_len             | STEPS stays = pattern length
        movel   (%sp)+,%d2              | restore delta
        movel   ef_cursor,%d1
        lea     ef_pulses,%a0
        tstl    %d1
        beq.s   1f
        lea     ef_rot,%a0
1:      movel   %a0@,%d0
        addl    %d2,%d0
        tstl    ef_cursor
        bne.s   4f
        | PULSE 0..STEPS
        tstl    %d0
        bpl.s   21f
        clrl    %d0
21:     movel   ef_steps,%d3
        cmpl    %d3,%d0
        ble.s   3f
        movel   %d3,%d0
        bra.s   3f
4:      | ROT 0..STEPS-1
        tstl    %d0
        bpl.s   41f
        clrl    %d0
41:     movel   ef_steps,%d3
        subql   #1,%d3
        cmpl    %d3,%d0
        ble.s   3f
        movel   %d3,%d0
3:      movel   %d0,%a0@
        bra.w   ef_draw
ef_nudge_rts:
        rts

| ---- draw helpers (y up from bottom; TEXT limit = -1) -------------------
| ef_text: d0=x, d1=y, a0=str; a5=surf. Clobbers d0/d1/a0/a1.
ef_text:
        movel   %a0,%sp@-
        pea     -1
        movel   %d1,%sp@-
        movel   %d0,%sp@-
        movel   %a5,%sp@-
        pea     FONT
        jsr     TEXT
        lea     %sp@(24),%sp
        rts

| ef_rtext: right-align a0 at x=d0, row d1. MUST reload a0 after TWIDTH
| (tuner parks the string in a6; we park the pointer in ef_rstr).
ef_rtext:
        movel   %a0,ef_rstr
        movel   %d0,ef_rx
        movel   %d1,ef_ry
        movel   %a0,%sp@-
        pea     -1
        pea     FONT
        jsr     TWIDTH
        lea     %sp@(12),%sp
        movel   ef_rx,%d1
        subl    %d0,%d1
        tstl    %d1
        bpl.s   1f
        moveq   #0,%d1                  | clamp if wider than the box
1:      movel   %d1,%d0
        movel   ef_ry,%d1
        movel   ef_rstr,%a0
        bra.w   ef_text

| ---- draw ---------------------------------------------------------------
| EUCLID  T1
| ─────────────
|  STEPS     16     (pattern length; not editable)
| >PULSE      5
|  ROT        0
| ■··■··■··■··     (preview)
ef_draw:
        tstl    ef_win
        beq.w   d9
        bsr.w   ef_sync_len             | STEPS := pattern length every paint
        lea     %sp@(-48),%sp
        movem.l %d2-%d7/%a2-%a6,%sp@
        movel   ef_win,%a2
        lea     %a2@(36),%a5
        movel   %a5,%sp@-
        jsr     CLEAR
        addql   #4,%sp

        moveq   #4,%d0
        moveq   #Y_TITLE,%d1
        lea     T_TITLE,%a0
        bsr.w   ef_text
        bsr.w   ef_fmt_tracks
        moveq   #X_VAL,%d0
        moveq   #Y_TITLE,%d1
        lea     ef_buf,%a0
        bsr.w   ef_rtext
        pea     1
        pea     WINW-4
        pea     Y_RULE
        pea     4
        movel   %a5,%sp@-
        jsr     RULE
        lea     %sp@(20),%sp

        moveq   #0,%d2
drow:   lea     L_STEPS,%a4
        moveq   #Y_ROW0,%d3
        tstl    %d2
        beq.s   dlbl
        lea     L_PULSES,%a4
        moveq   #Y_ROW1,%d3
        moveq   #1,%d0
        cmpl    %d2,%d0
        beq.s   dlbl
        lea     L_ROT,%a4
        moveq   #Y_ROW2,%d3
| cursor 0 -> PULSE row, cursor 1 -> ROT row; STEPS never focused
dlbl:   tstl    %d2
        beq.s   dlab
        movel   %d2,%d0
        subql   #1,%d0
        cmpl    ef_cursor,%d0
        bne.s   dlab
        moveq   #3,%d0
        movel   %d3,%d1
        lea     T_MARK,%a0
        bsr.w   ef_text
dlab:   moveq   #X_LAB,%d0
        movel   %d3,%d1
        movel   %a4,%a0
        bsr.w   ef_text

        lea     ef_steps,%a0
        tstl    %d2
        beq.s   dval
        lea     ef_pulses,%a0
        moveq   #1,%d0
        cmpl    %d2,%d0
        beq.s   dval
        lea     ef_rot,%a0
dval:   movel   %a0@,-(%sp)
        pea     VFMT
        pea     ef_buf
        jsr     SPRINTF
        lea     %sp@(12),%sp
        moveq   #X_VAL,%d0
        movel   %d3,%d1
        lea     ef_buf,%a0
        bsr.w   ef_rtext

        addql   #1,%d2
        moveq   #3,%d0
        cmpl    %d0,%d2
        bcs.w   drow

        bsr.w   ef_draw_pat

        moveq   #1,%d0
        movel   %d0,SCRDIRTY
        movem.l %sp@,%d2-%d7/%a2-%a6
        lea     %sp@(48),%sp
d9:     rts

| ef_fmt_tracks: write "T135" (1-based) for ef_targets into ef_buf.
ef_fmt_tracks:
        lea     ef_buf,%a0
        moveb   #0x54,%a0@+             | 'T'
        moveq   #0,%d2
        movel   ef_targets,%d3
        bne.s   1f
        moveb   #0x2d,%a0@+             | '-'
        clrb    %a0@
        rts
1:      btst    %d2,%d3
        beq.s   2f
        moveq   #0x31,%d0               | '1'
        addl    %d2,%d0
        moveb   %d0,%a0@+
2:      addql   #1,%d2
        moveq   #8,%d0
        cmpl    %d0,%d2
        bcs.s   1b
        clrb    %a0@
        rts

| ef_draw_pat: bar of n cells; a5 = surf. Same (i·k)%n < k law as the writer.
ef_draw_pat:
        movel   ef_steps,%d5
        moveq   #1,%d0
        cmpl    %d0,%d5
        bge.s   p1
        moveq   #1,%d5
p1:     moveq   #64,%d0
        cmpl    %d0,%d5
        ble.s   p2
        moveq   #64,%d5
p2:     movel   ef_pulses,%d4
        tstl    %d4
        bpl.s   p3
        clrl    %d4
p3:     cmpl    %d5,%d4
        ble.s   p4
        movel   %d5,%d4
p4:     movel   ef_rot,%d6
        tstl    %d6
        bpl.s   p5
        clrl    %d6
p5:     cmpl    %d5,%d6
        bcs.s   p6
        clrl    %d6
p6:     moveq   #0,%d2                  | step i
ploop:
        | x0 = 4 + i*(WINW-8)/n
        movel   %d2,%d0
        moveq   #WINW-8,%d1
        mulu.w  %d1,%d0
        divul   %d5,%d0                 | 32/32 like tuner.s
        addql   #4,%d0
        movel   %d0,%a1                 | park x0
        | x1 = 4 + (i+1)*(WINW-8)/n - 2
        movel   %d2,%d1
        addql   #1,%d1
        moveq   #WINW-8,%d3
        mulu.w  %d3,%d1
        divul   %d5,%d1
        addql   #2,%d1
        movel   %d1,%a2                 | park x1
        | idx = (i + n - rot) % n
        movel   %d2,%d3
        addl    %d5,%d3
        subl    %d6,%d3
pmod:   cmpl    %d5,%d3
        bcs.s   phit
        subl    %d5,%d3
        bra.s   pmod
phit:   moveq   #0,%d7
        tstl    %d4
        beq.s   pdraw
        movel   %d3,%d0
        mulu.w  %d4,%d0
        divu.w  %d5,%d0
        clrl    %d3
        swap    %d0
        move.w  %d0,%d3
        cmpl    %d4,%d3
        bcc.s   pdraw
        moveq   #1,%d7
pdraw:  movel   %a1,%d0                 | x0
        movel   %a2,%d1                 | x1
        cmpl    %d0,%d1
        bge.s   pbox
        movel   %d0,%d1                 | at least 1 px wide
pbox:   tstl    %d7
        beq.s   prest
        pea     1
        pea     Y_PAT+PAT_H
        movel   %d1,%sp@-
        pea     Y_PAT
        movel   %d0,%sp@-
        movel   %a5,%sp@-
        jsr     BOX
        lea     %sp@(24),%sp
        bra.s   pnext
prest:  pea     1
        pea     Y_PAT+1
        movel   %d1,%sp@-
        pea     Y_PAT
        movel   %d0,%sp@-
        movel   %a5,%sp@-
        jsr     BOX
        lea     %sp@(24),%sp
pnext:  addql   #1,%d2
        cmpl    %d5,%d2
        bcs.w   ploop
        rts

| ---- fill: Euclidean trigs on ef_targets --------------------------------
ef_fill:
        bsr.w   ef_sync_len             | n = pattern length
        lea     %sp@(-36),%sp
        movem.l %d2-%d7/%a2-%a4,%sp@
        movel   ef_targets,%d7
        beq.w   fout
        moveal  DBPTR,%a2
        moveq   #0,%d2
        moveb   UI_PTN,%d2
        movel   #PTN_STR,%d0
        mulu.l  %d0,%d2
        addal   %d2,%a2                 | a2 = pattern base in blob

        movel   ef_steps,%d5
        moveq   #1,%d0
        cmpl    %d0,%d5
        bge.s   1f
        moveq   #1,%d5
1:      moveq   #64,%d0
        cmpl    %d0,%d5
        ble.s   2f
        moveq   #64,%d5
2:      movel   ef_pulses,%d4
        tstl    %d4
        bpl.s   3f
        clrl    %d4
3:      cmpl    %d5,%d4
        ble.s   4f
        movel   %d5,%d4
4:      movel   ef_rot,%d3
        tstl    %d3
        bpl.s   5f
        clrl    %d3
5:      cmpl    %d5,%d3
        bcs.s   6f
        clrl    %d3
6:      movel   %d3,%d6                 | rot

        moveq   #0,%d2                  | track
tloop:  btst    %d2,%d7
        beq.s   tnext
        movel   %d2,%d0
        movel   #TRK_STR,%d1
        mulu.l  %d1,%d0
        lea     %a2@(0,%d0:l),%a3       | a3 = TRAC
        movel   %d5,-(%sp)
        movel   %d4,-(%sp)
        movel   %d6,-(%sp)
        movel   %a3,-(%sp)
        bsr.w   ef_write_mask
        lea     %sp@(16),%sp
        | battery mirror of mask 0 (8 bytes)
        moveq   #0,%d0
        moveb   UI_PTN,%d0
        movel   #PTN_STR,%d1
        mulu.l  %d1,%d0
        movel   %d2,%d1
        movel   #TRK_STR,%d3
        mulu.l  %d3,%d1
        addl    %d1,%d0
        addil   #MIRROR,%d0
        moveal  %d0,%a4
        moveq   #7,%d0
mcopy:  moveb   %a3@(0,%d0:l),%d1
        moveb   %d1,%a4@(0,%d0:l)
        subql   #1,%d0
        bpl.s   mcopy
tnext:  addql   #1,%d2
        moveq   #8,%d0
        cmpl    %d0,%d2
        bcs.s   tloop

        moveal  DBPTR,%a0
        addal   #DIRTY_OFF,%a0
        moveq   #1,%d0
        movel   %d0,%a0@
        moveal  #DIRTY_G,%a0
        movel   %d0,%a0@
        jsr     NOTIFY
fout:   movem.l %sp@,%d2-%d7/%a2-%a4
        lea     %sp@(36),%sp
        rts

| ef_write_mask(trac, rot, k, n) -- stack args after bsr. Clears then sets
| Euclidean hits on steps 0..n-1 of mask 0; leaves n..63 alone.
ef_write_mask:
        lea     -28(%sp),%sp
        movem.l %d2-%d7/%a2,(%sp)
        moveal  32(%sp),%a2             | 28 + 4 return = 32
        movel   36(%sp),%d6
        movel   40(%sp),%d4
        movel   44(%sp),%d5
        moveq   #0,%d2
1:      cmpl    %d5,%d2
        bcc.s   9f
        bsr.w   ef_bit_addr
        moveb   %a0@,%d1
        move.l  %d0,%d3
        not.l   %d3
        and.l   %d3,%d1
        moveb   %d1,%a0@
        movel   %d2,%d3
        addl    %d5,%d3
        subl    %d6,%d3
2:      cmpl    %d5,%d3
        bcs.s   3f
        subl    %d5,%d3
        bra.s   2b
3:      tstl    %d4
        beq.s   8f
        movel   %d3,%d0
        mulu.w  %d4,%d0
        divu.w  %d5,%d0
        clrl    %d1
        swap    %d0
        move.w  %d0,%d1
        cmpl    %d4,%d1
        bcc.s   8f
        bsr.w   ef_bit_addr
        moveb   %a0@,%d1
        or.l    %d0,%d1
        moveb   %d1,%a0@
8:      addql   #1,%d2
        bra.s   1b
9:      movem.l (%sp),%d2-%d7/%a2
        lea     28(%sp),%sp
        rts

| d2=step, a2=trac -> a0=&byte, d0=bitmask. Clobbers d0,d1,a0.
ef_bit_addr:
        movel   %d2,%d1
        lsr.l   #3,%d1
        moveq   #7,%d0
        subl    %d1,%d0
        lea     %a2@(0,%d0:l),%a0
        movel   %d2,%d1
        andil   #7,%d1
        moveq   #1,%d0
        lsll    %d1,%d0
        rts

| ---- layer --------------------------------------------------------------
        .balign 4
EF_LAYER:
        .long   0, EF_KEYS, EF_ENCS, 0, 0, -1, -1
EF_KEYS:
        .byte   0x1b, 0                 | PAGE closes
        .long   ef_close, 0, 0, 0, 0
        .word   0, 0
        .byte   0x31, 0                 | YES
        .long   ef_yes, 0, 0, 0, 0
        .word   0, 0
        .byte   0x32, 0                 | NO
        .long   ef_no, 0, 0, 0, 0
        .word   0, 0
        .byte   0x33, 0                 | UP
        .long   ef_up, 0, 0, 0, 0
        .word   0, 0
        .byte   0x20, 0                 | DOWN
        .long   ef_down, 0, 0, 0, 0
        .word   0, 0
        .byte   0x34, 0                 | LEFT
        .long   ef_left, 0, 0, 0, 0
        .word   0, 0
        .byte   0x21, 0                 | RIGHT
        .long   ef_right, 0, 0, 0, 0
        .word   0, 0
        .byte   0xff, 0
        .long   0, 0, 0, 0, 0
        .word   0, 0
EF_ENCS:
        .byte   0, 0                    | A = PULSE
        .long   ef_enc, 0, 0, 0, 0
        .byte   1, 0                    | B = ROT
        .long   ef_enc, 0, 0, 0, 0
        .byte   6, 0                    | LEVEL = focused row
        .long   ef_level, 0, 0, 0, 0
        .byte   0xff, 0
        .long   0, 0, 0, 0, 0

T_TITLE:  .asciz "EUCLID"
T_FILLED: .asciz "EUCLID FILL"
T_MARK:   .asciz ">"
L_STEPS:  .asciz "STEPS"
L_PULSES: .asciz "PULSE"
L_ROT:    .asciz "ROT"
VFMT:     .asciz "%d"
        .balign 4

        .data
        .balign 4
        .globl  ef_win, ef_steps, ef_pulses, ef_rot, ef_cursor, ef_targets
ef_win:     .long 0
ef_steps:   .long 16
ef_pulses:  .long 5                     | match filter EUCLID default
ef_rot:     .long 0
ef_cursor:  .long 0
ef_targets: .long 0
ef_rx:      .long 0
ef_ry:      .long 0
ef_rstr:    .long 0
ef_buf:     .space 24
