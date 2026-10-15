/* C ABI adapters. Native/public Harmony helpers use register arguments.
 * C retains d2-d7/a2-a6; the called helpers preserve that set.
 */
    .text
/* Register ABI wrappers for the existing lifecycle hooks. Preserve all
 * registers except a documented result, including C's volatile a1. */
    .global hd_reset,hd_ready_all,hd_bank_reset,hd_bank_loaded,hd_nv_save,hd_nv_restore
hd_reset:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr hd_reset_c
    jsr hd_events_reset_c
    jsr hd_operations_reset_c
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_ready_all:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr hd_ready_all_c
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_bank_reset:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr hd_bank_reset_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_bank_loaded:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr hd_bank_loaded_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_nv_save:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr hd_nv_save_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_nv_restore:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr hd_nv_restore_c
    addq.l #4,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts

/* d0=bank, a0=complete packed payload; export returns d0=valid. */
    .global hd_export,hd_import,hd_payload_hash,hd_native_hash
hd_export:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %a0,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_export_c
    addq.l #8,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
hd_import:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %a0,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_import_c
    addq.l #8,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* a0=complete payload -> d0=FNV, d1=valid. */
hd_payload_hash:
    lea -12(%sp),%sp
    movem.l %d2/%a0-%a1,(%sp)
    move.l %a0,-(%sp)
    jsr hd_payload_valid_c
    move.l %d0,%d2
    /* A C sibling call may rewrite its incoming argument slot. */
    move.l 8(%sp),(%sp)
    jsr hd_payload_hash_c
    addq.l #4,%sp
    move.l %d2,%d1
    movem.l (%sp),%d2/%a0-%a1
    lea 12(%sp),%sp
    rts
/* d0=bank, d1=native NOTE/trig fingerprint -> d0=extended fingerprint. */
hd_native_hash:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_native_hash_c
    addq.l #8,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts

    .global hd_set,hd_prepare,hd_sequence_prepare,hd_stage,hd_stage_copy,hd_fire
/* Explicit selected-Part mode edit. Native recall does not use this setter. */
hd_set:
    cmpi.l #7,%d0
    bhi.w .set_invalid
    cmpi.l #2,%d1
    bhi.w .set_invalid
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    jsr mp_ui_context
    tst.l %d0
    bmi.w .set_unavailable
    move.l (%sp),%d0
    jsr mh_get
    cmp.l 4(%sp),%d0
    beq.s .set_done
    move.l 4(%sp),-(%sp)
    move.l 4(%sp),-(%sp)
    jsr hd_mode_c
    move.l (%sp),%d0
    move.l 4(%sp),%d1
    jsr hd_record_modes
    /* Each queued event publishes under its own bounded mask. Conversion
     * does not keep interrupts disabled for the entire queue scan. */
    move.l 4(%sp),-(%sp)
    move.l 4(%sp),-(%sp)
    jsr hd_events_mode_c
    addq.l #8,%sp
    move.w %sr,%d0
    move.l %d0,-(%sp)
    move.w #0x2700,%sr
    move.l 4(%sp),%d0
    move.l 8(%sp),%d1
    jsr mh_set_native
    move.l 4(%sp),%d0
    lea hd_busy,%a0
    clr.b (%a0,%d0.l)
    move.l (%sp)+,%d0
    move.w %d0,%sr
    addq.l #8,%sp
    jsr mp_ui_context
    lsr.l #2,%d0
    jsr ch_nv_save
.set_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    moveq #1,%d0
    rts
.set_unavailable:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
.set_invalid:
    moveq #0,%d0
    rts

/* d0 native pitch, d1 track -> d0 resolved pitch, other registers kept. */
hd_prepare:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_prepare_c
    addq.l #8,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
/* d0 track, a0 native four-note scratch. OFF leaves every byte alone. */
hd_sequence_prepare:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l (%sp),%d1
    move.l 8(%sp),%a0
    moveq #0,%d0
    move.b (%a0),%d0
    jsr hd_prepare
    move.l 8(%sp),%a0
    move.b %d0,(%a0)
.sequence_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* bank/pattern/track/step/slot in d0..d4. */
hd_stage:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d4,-(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_event_stage_c
    lea 20(%sp),%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
hd_stage_copy:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d0,-(%sp)
    jsr hd_event_copy_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* d0 slot index, d5 track, a0 native source record. */
hd_fire:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d5,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_event_fire_c
    addq.l #8,%sp
    tst.l %d0
    bmi.s .fire_done
    move.l 8(%sp),%a0
    move.b %d0,(%a0)
.fire_done:
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

    .global hd_capture,hd_record
/* UI physical note -> captured degree; release keeps physical pitch. */
hd_capture:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_capture_c
    addq.l #8,%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
    .global hd_capture_message,hd_record_consume,hd_record_modes
/* a1 message,d0 physical note,d1 track -> code, other registers kept. */
hd_capture_message:
    lea -12(%sp),%sp
    movem.l %d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    move.l %a1,-(%sp)
    jsr hd_capture_message_c
    lea 12(%sp),%sp
    movem.l (%sp),%d1/%a0-%a1
    lea 12(%sp),%sp
    rts
/* a2 queued physical message; all registers kept. */
hd_record_consume:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %a2,-(%sp)
    jsr hd_record_consume_c
    addq.l #4,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* d0 track,d1 new mode, selected Part only; all registers kept. */
hd_record_modes:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_record_modes_c
    addq.l #8,%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
    .global hd_record_sync
/* Reconcile the native recorder's destination before atomic publication. */
hd_record_sync:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_sync_c
    lea 12(%sp),%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
/* d0 bank, d1 pattern, d2 track, d3 step, d4 captured degree.
 * The recorder holds its short root-publication mask; it saves NV afterward. */
hd_record:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d4,-(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_record_publish_c
    lea 20(%sp),%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts

    .global hd_forget
/* d0 bank, d1 pattern, d2 track, d3 step; all registers preserved. */
hd_forget:
    lea -16(%sp),%sp
    movem.l %d0-%d1/%a0-%a1,(%sp)
    move.l %d3,-(%sp)
    move.l %d2,-(%sp)
    move.l %d1,-(%sp)
    move.l %d0,-(%sp)
    jsr hd_forget_c
    lea 16(%sp),%sp
    movem.l (%sp),%d0-%d1/%a0-%a1
    lea 16(%sp),%sp
    rts
