/* CHRD companion files. File I/O follows the repository's PLOCKS P2
 * APIs, with dedicated storage, validated bank/version/size/value range,
 * payload checksum and native NOTE/trig fingerprint before publication.
 * Read errors never partially publish into the live lock table.
 */
        .set    F_OPEN,     0x40016864      | (fo, path, mode, buffer, size) -> <0 error
        .set    F_READ,     0x40016564      | (fo, dst, n) -> 1
        .set    F_WRITE,    0x400166b8      | (fo, src, n) -> 1
        .set    F_CLOSE,    0x4001677c      | (fo)
        .set    F_COPY,     0x40016388      | (dst path, src path, 0) -> <0 error
        .set    PROJDIR,    0x40025230      | (0, 0) -> the project directory
        .set    SPRINTF,    0x40013a08
        .set    IOB_LEN,    0x1000

    .set BANK_B,8192
    .set FILE_B,15104
    .set FILE_MAGIC,0x48445034 /* HDP4: packed roots plus ACC lanes */
    .set FILE_VERSION,4
    .set FILE_NONE,0x48445030  /* HDP0: explicit empty companion */
    .text
    .global ch_st_bankw_guard,ch_st_bankcopy_guard,ch_st_bankcopy_done
    .global ch_st_loadall_post,ch_st_loadmask_post,ch_st_tocs1,ch_st_fromcs1
    .global ch_st_newproj,ch_st_newproj_post
    .global ch_file_read,ch_file_write,ch_native_hash
path:   lea     %sp@(-8),%sp
        movem.l %d2/%a2,%sp@
        movel   %d0,%d2
        addql   #1,%d2
        moveal  %a0,%a2
        clrl    %sp@-
        clrl    %sp@-
        jsr     PROJDIR
        addql   #8,%sp
        movel   %d2,%sp@-
        movel   %d0,%sp@-
        movel   %a2,%sp@-
        pea     PATH
        jsr     SPRINTF
        lea     %sp@(16),%sp
        movem.l %sp@,%d2/%a2
        lea     %sp@(8),%sp
        rts

| fopen: a0 = path, a1 = mode -> d0 (< 0: failed).
fopen:  pea     IOB_LEN
        pea     IOB
        movel   %a1,%sp@-
        movel   %a0,%sp@-
        pea     FOBJ
        jsr     F_OPEN
        lea     %sp@(20),%sp
        rts

| fio: a0 = buffer, d0 = length, a1 = F_READ or F_WRITE -> d0 (1 = done).
fio:    movel   %d0,%sp@-
        movel   %a0,%sp@-
        pea     FOBJ
        jsr     %a1@
        lea     %sp@(12),%sp
        rts

fclose: pea     FOBJ
        jsr     F_CLOSE
        addql   #4,%sp
        rts

| bank_at: d0 = bank -> a0 = its CHRD bank in ch_lock_table.
bank_at:
        movel   #BANK_B,%d1
        mulu.l  %d1,%d0
        addil   #ch_lock_table,%d0
        moveal  %d0,%a0
        rts

| blank: d0 = bank -> its CHRD bank all 0xff. Keeps d2-d7/a2-a6.
blank:
        jsr hd_bank_reset
        bsr.w   bank_at
        moveq   #-1,%d0
        movel   #BANK_B/4,%d1
bl_loop:
        movel   %d0,%a0@+
        subql   #1,%d1
        bne.s   bl_loop
        rts

| hdr: d0 = bank -> HDR filled.
hdr:    lea     HDR,%a0
        movel   #FILE_MAGIC,%a0@
        moveq   #FILE_VERSION,%d1
        movel   %d1,%a0@(4)
        movel   %d0,%a0@(8)
        movel   #FILE_B,%d1
        movel   %d1,%a0@(12)
        rts

rename: movel   %a1,%sp@-
        moveal  %a0,%a2                | a2 = the last "/bank" seen
        suba.l  %a3,%a3
        moveq   #0,%d0
rn_copy:
        moveb   %a0@+,%d1
        moveb   %d1,%a1@+
        addql   #1,%d0
        cmpil   #259,%d0
        bcc.s   rn_none
        tstb    %d1
        beq.s   rn_end
        cmpib   #'/',%d1
        bne.s   rn_copy
        moveb   %a0@,%d1
        cmpib   #'b',%d1
        bne.s   rn_copy
        moveb   %a0@(1),%d1
        cmpib   #'a',%d1
        bne.s   rn_copy
        moveb   %a0@(2),%d1
        cmpib   #'n',%d1
        bne.s   rn_copy
        moveb   %a0@(3),%d1
        cmpib   #'k',%d1
        bne.s   rn_copy
        moveal  %a1,%a3                | a3 = where "bank" lands in the copy
        bra.s   rn_copy
rn_end: movel   %a3,%d0
        beq.s   rn_none
        moveb   #'h',%a3@+
        moveb   #'d',%a3@+
        moveb   #'e',%a3@+
        moveb   #'g',%a3@
        moveal  %sp@+,%a1
        moveq   #1,%d0
        rts
rn_none:
        moveal  %sp@+,%a1
        moveq   #0,%d0
        rts

/* d0 bank -> d0 FNV1a of native MIDI root bytes + note trig bitmap.
 * The identity covers all 16 patterns, all tracks and all 64 steps.
 * Unrelated CC edits and native transient/dirty fields do not invalidate it.
 */
ch_native_hash:
    move.l %d0,-(%sp)
    lea -28(%sp),%sp
    movem.l %d1-%d5/%a0-%a1,(%sp)
    move.l #0x9b340,%d1
    mulu.l %d1,%d0
    lea 0x400e21e0,%a0
    adda.l %d0,%a0
    lea 0x48d0(%a0),%a0
    move.l #0x811c9dc5,%d0
    move.l #0x01000193,%d5
    moveq #16,%d4
.hash_pattern:
    moveq #8,%d3
.hash_track:
    move.l %a0,%a1
    moveq #8,%d2
.hash_trig:
    moveq #0,%d1
    move.b (%a1)+,%d1
    eor.l %d1,%d0
    mulu.l %d5,%d0
    subq.l #1,%d2
    bne.s .hash_trig
    lea 0x30(%a0),%a1
    moveq #64,%d2
.hash_root:
    moveq #0,%d1
    move.b (%a1),%d1
    eor.l %d1,%d0
    mulu.l %d5,%d0
    lea 32(%a1),%a1
    subq.l #1,%d2
    bne.s .hash_root
    adda.l #0x8b0,%a0
    subq.l #1,%d3
    bne.s .hash_track
    adda.l #0x8ed8-8*0x8b0,%a0
    subq.l #1,%d4
    bne.s .hash_pattern
    movem.l (%sp),%d1-%d5/%a0-%a1
    lea 28(%sp),%sp
    move.l %d1,-(%sp)
    move.l %d0,%d1
    move.l 4(%sp),%d0
    jsr hd_native_hash
    move.l (%sp)+,%d1
    addq.l #4,%sp
    rts
/* a0 payload -> d0 checksum, d1=1 valid byte range / 0 invalid. */
.payload_hash:
    jmp hd_payload_hash
/* d0 bank -> 1 complete, negative error. Header is 32 bytes BE:
 * magic, version, bank, length, FNV payload, FNV native identity, 0, 0.
 */
ch_file_write:
    lea -12(%sp),%sp
    movem.l %d2-%d3/%a2,(%sp)
    move.l %d0,%d2
    lea ch_lock_status,%a0
    moveq #0,%d0
    move.b (%a0,%d2.l),%d0
    cmpi.l #2,%d0
    beq.w .wr_refuse
    cmpi.l #3,%d0
    beq.w .wr_refuse
    move.l %d2,%d0
    bsr.w hdr
    move.l %d2,%d0
    bsr.w ch_native_hash
    move.l %d0,HDR+20
    clr.l HDR+24
    clr.l HDR+28
    move.l %d2,%d0
    lea PAYLOAD,%a0
    jsr hd_export
    tst.l %d0
    beq.w .wr_fail
    lea PAYLOAD,%a0
    bsr.w .payload_hash
    move.l %d0,HDR+16
    tst.l %d1
    beq.w .wr_fail
    move.l %d2,%d0
    lea FMT_WORK,%a0
    bsr.w path
    lea PATH,%a0
    lea MODE_W,%a1
    bsr.w fopen
    tst.l %d0
    bmi.s .wr_fail
    lea HDR,%a0
    moveq #32,%d0
    lea F_WRITE,%a1
    bsr.w fio
    move.l %d0,%d3
    cmpi.l #1,%d0
    bne.s .wr_close
    lea PAYLOAD,%a0
    move.l #FILE_B,%d0
    lea F_WRITE,%a1
    bsr.w fio
    move.l %d0,%d3
.wr_close:
    bsr.w fclose
    tst.l %d0
    bmi.s .wr_fail
    cmpi.l #1,%d3
    bne.s .wr_fail
    moveq #1,%d0
    lea ch_lock_status,%a0
    move.b %d0,(%a0,%d2.l)
    bra.s .wr_done
.wr_fail:
    lea ch_lock_status,%a0
    moveq #4,%d0
    move.b %d0,(%a0,%d2.l)
.wr_refuse:
    moveq #-7,%d0
.wr_done:
    movem.l (%sp),%d2-%d3/%a2
    lea 12(%sp),%sp
    rts
ch_file_read:
    lea -12(%sp),%sp
    movem.l %d2-%d3/%a2,(%sp)
    move.l %d0,%d2
    lea FMT_WORK,%a0
    bsr.w path
    pea PATH
    move.l 0x46c823fa,%a0 /* native path-exists callback */
    jsr (%a0)
    addq.l #4,%sp
    moveq #0,%d3 /* a missing companion is ordinary, not corrupted */
    tst.l %d0
    beq.w .rd_blank
    moveq #2,%d3 /* existing but unreadable/invalid => explicit diagnostic */
    bmi.w .rd_blank
    lea PATH,%a0
    lea MODE_R,%a1
    bsr.w fopen
    tst.l %d0
    bmi.w .rd_blank
    lea HDR,%a0
    moveq #32,%d0
    lea F_READ,%a1
    bsr.w fio
    cmpi.l #1,%d0
    bne.w .rd_bad
    move.l HDR,%d0
    cmpi.l #FILE_NONE,%d0 /* explicit empty companion */
    beq.w .rd_none
    cmpi.l #FILE_MAGIC,%d0
    bne.w .rd_bad
    move.l HDR+4,%d0
    cmpi.l #FILE_VERSION,%d0
    bne.w .rd_bad
    cmp.l HDR+8,%d2
    bne.w .rd_bad
    move.l HDR+12,%d0
    cmpi.l #FILE_B,%d0
    bne.w .rd_bad
    move.l HDR+24,%d0
    or.l HDR+28,%d0
    bne.w .rd_bad
    pea FOBJ
    jsr 0x400148d4 /* actual byte length, not buffered sector EOF */
    addq.l #4,%sp
    cmpi.l #FILE_B+32,%d0
    bne.w .rd_bad
    lea PAYLOAD,%a0
    move.l #FILE_B,%d0
    lea F_READ,%a1
    bsr.w fio
    cmpi.l #1,%d0
    bne.w .rd_bad
    lea PAYLOAD,%a0
    bsr.w .payload_hash
    tst.l %d1
    beq.w .rd_bad
    cmp.l HDR+16,%d0
    bne.w .rd_bad
    moveq #3,%d3
    move.l %d2,%d0
    bsr.w ch_native_hash
    cmp.l HDR+20,%d0
    bne.w .rd_bad
    bsr.w fclose
    move.l %d2,%d0
    lea PAYLOAD,%a0
    jsr hd_import
    moveq #1,%d3
    bra.w .rd_status
.rd_none:
    pea FOBJ
    jsr 0x400148d4
    addq.l #4,%sp
    cmpi.l #32,%d0
    bne.s .rd_bad
    lea HDR+4,%a0
    moveq #7,%d0
.rd_marker:
    tst.l (%a0)+
    bne.s .rd_bad
    subq.l #1,%d0
    bne.s .rd_marker
    moveq #0,%d3
.rd_bad:
    bsr.w fclose
.rd_blank:
    move.l %d2,%d0
    bsr.w blank
.rd_status:
    move.l %d2,%d0
    jsr hd_bank_loaded
    lea ch_lock_status,%a0
    move.b %d3,(%a0,%d2.l)
    movem.l (%sp),%d2-%d3/%a2
    lea 12(%sp),%sp
    rts

/* STORE checked phase: fail before native/P2 saves if any companion fails.
 * d1 = bank mask. STORE owns the native error exit and register restoration. */
ch_st_bankw_guard:
    move.l %d1,-(%sp)
    jsr ch_lock_init
    move.l (%sp)+,%d3
    moveq #0,%d4
.sb_loop:
    btst %d4,%d3
    beq.s .sb_next
    move.l %d4,%d0
    bsr.w ch_file_write
    tst.l %d0
    bmi.s .sb_return
.sb_next:
    addq.l #1,%d4
    cmpi.l #16,%d4
    bne.s .sb_loop
    moveq #0,%d0
.sb_return:
    rts

/* Native loads finished; identity uses the newly loaded bank. */
ch_st_loadall_post:
    lea -12(%sp),%sp
    movem.l %d0/%d2-%d3,(%sp)
    jsr ch_lock_init
    clr.l NEEDFILE
    moveq #0,%d2
.la_loop:
    move.l %d2,%d0
    bsr.w ch_file_read
    addq.l #1,%d2
    cmpi.l #16,%d2
    bne.s .la_loop
    moveq #0,%d0
    move.b 0x80000002,%d0
    jsr ch_nv_save
    movem.l (%sp),%d0/%d2-%d3
    lea 12(%sp),%sp
    rts
ch_st_loadmask_post:
    move.l %d1,-(%sp)
    jsr ch_lock_init
    move.l (%sp)+,%d3
    moveq #0,%d2
.lm_loop:
    btst %d2,%d3
    beq.s .lm_next
    move.l %d2,%d0
    bsr.w ch_file_read
.lm_next:
    addq.l #1,%d2
    cmpi.l #16,%d2
    bne.s .lm_loop
    move.l NEEDFILE,%d0
    beq.s .lm_done
    clr.l NEEDFILE
    subq.l #1,%d0
    bsr.w ch_file_read
.lm_done:
    moveq #0,%d0
    move.b 0x80000002,%d0
    jsr ch_nv_save
    rts

ch_st_tocs1:
    move.l %d0,-(%sp)
    jsr ch_lock_init
    move.l (%sp)+,%d0
    jmp ch_nv_save

/* STORE dispatches P2 first, then Harmony, after the native CS1 restore. */
ch_st_fromcs1:
    move.l %d0,-(%sp)
    jsr ch_lock_init
    move.l (%sp)+,%d0
    move.l %d0,%d1
    jsr ch_nv_restore
    tst.l %d0
    bne.s .cs_restored
    addq.l #1,%d1
    move.l %d1,NEEDFILE
.cs_restored:
    rts

ch_st_newproj_post:
    jmp hd_ready_all
ch_st_newproj:
    lea -12(%sp),%sp
    movem.l %d0-%d1/%a0,(%sp)
    jsr ch_lock_init
    lea ch_lock_table,%a0
    moveq #-1,%d0
    move.l #131072/4,%d1
.np_loop:
    move.l %d0,(%a0)+
    subq.l #1,%d1
    bne.s .np_loop
    move.l %d0,ch_nv_bank
    clr.l NEEDFILE
    lea ch_lock_status,%a0
    clr.l (%a0)
    clr.l 4(%a0)
    clr.l 8(%a0)
    clr.l 12(%a0)
    jsr hd_track_invalidate_c
    jsr hd_reset
    movem.l (%sp),%d0-%d1/%a0
    lea 12(%sp),%sp
    rts

/* Copy only after stock succeeded. Missing companion creates an explicit
 * HDP0 marker, preventing an older destination's CHRD from surviving. */
ch_st_bankcopy_guard:
    move.l %d1,%a0
    jmp ch_copy_guard

/* d0 = destination, d1 = source; STORE calls only after native success. */
ch_st_bankcopy_done:
    move.l %d0,%a3
    move.l %d1,%a2
    moveq #0,%d0
    lea -16(%sp),%sp
    movem.l %d0/%d2/%a2-%a3,(%sp)
    move.l 8(%sp),%a0
    lea PSRC,%a1
    bsr.w rename
    tst.l %d0
    beq.w .fc_out
    move.l 12(%sp),%a0
    lea PATH,%a1
    bsr.w rename
    tst.l %d0
    beq.w .fc_out
    clr.l -(%sp)
    pea PSRC
    pea PATH
    jsr F_COPY
    lea 12(%sp),%sp
    tst.l %d0
    bpl.s .fc_out
    /* An existing but unreadable source is an error, never an empty bank. */
    pea PSRC
    move.l 0x46c823fa,%a0
    jsr (%a0)
    addq.l #4,%sp
    tst.l %d0
    bne.s .fc_fail
.fc_absent:
    lea PATH,%a0
    lea MODE_W,%a1
    bsr.w fopen
    tst.l %d0
    bmi.s .fc_fail
    lea HDR,%a0
    clr.l (%a0)
    clr.l 4(%a0)
    clr.l 8(%a0)
    clr.l 12(%a0)
    clr.l 16(%a0)
    clr.l 20(%a0)
    clr.l 24(%a0)
    clr.l 28(%a0)
    move.l #FILE_NONE,%d0
    move.l %d0,(%a0)
    moveq #32,%d0
    lea F_WRITE,%a1
    bsr.w fio
    move.l %d0,%d2
    bsr.w fclose
    tst.l %d0
    bmi.s .fc_fail
    cmpi.l #1,%d2
    beq.s .fc_out
.fc_fail:
    moveq #-7,%d0
    move.l %d0,(%sp)
.fc_out:
    movem.l (%sp),%d0/%d2/%a2-%a3
    lea 16(%sp),%sp
.fc_return:
    rts
FMT_WORK: .asciz "%s/hdeg%02d.work"
MODE_R: .asciz "r"
MODE_W: .asciz "w"
    .balign 4
NEEDFILE: .long 0
    .bss
    .balign 4
FOBJ: .space 24
HDR: .space 32
PATH: .space 260
PSRC: .space 260
IOB: .space IOB_LEN
PAYLOAD: .space FILE_B
EXTRA: .space 4

/* Native project SAVE can continue to its store-copy phase after a failed
 * working save. Protect the last stored bank before ANY native copy occurs.
 * Only bankNN.work sources are blocked: strd -> work remains a recovery path.
 * a0 source path -> d0=0 allowed, -7 blocked; preserves nonvolatile registers.
 */
    .text
    .global ch_copy_guard
ch_copy_guard:
    lea -8(%sp),%sp
    movem.l %d2/%a2,(%sp)
    move.l %a0,%a2
.cg_basename:
    move.b (%a0)+,%d0
    beq.s .cg_prefix
    cmpi.b #'/',%d0
    bne.s .cg_basename
    move.l %a0,%a2
    bra.s .cg_basename
.cg_prefix:
    lea .cg_bank,%a1
    moveq #4,%d1
.cg_bank_loop:
    move.b (%a2)+,%d0
    cmp.b (%a1)+,%d0
    bne.w .cg_allow
    subq.l #1,%d1
    bne.s .cg_bank_loop
    moveq #0,%d0
    move.b (%a2)+,%d0
    subi.l #48,%d0
    cmpi.l #9,%d0
    bhi.s .cg_allow
    moveq #10,%d2
    mulu.l %d2,%d0
    moveq #0,%d1
    move.b (%a2)+,%d1
    subi.l #48,%d1
    cmpi.l #9,%d1
    bhi.s .cg_allow
    add.l %d1,%d0
    subq.l #1,%d0
    cmpi.l #15,%d0
    bhi.s .cg_allow
    move.l %d0,%d2
    lea .cg_work,%a1
.cg_suffix:
    move.b (%a2)+,%d0
    cmp.b (%a1)+,%d0
    bne.s .cg_allow
    tst.b %d0
    bne.s .cg_suffix
    lea ch_lock_status,%a0
    moveq #0,%d0
    move.b (%a0,%d2.l),%d0
    cmpi.l #2,%d0
    bcs.s .cg_allow
    moveq #-7,%d0
    bra.s .cg_done
.cg_allow:
    moveq #0,%d0
.cg_done:
    movem.l (%sp),%d2/%a2
    addq.l #8,%sp
    rts
.cg_bank: .ascii "bank"
.cg_work: .asciz ".work"
