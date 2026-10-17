#ifndef HARMONY_DEGREES_CORE_H
#define HARMONY_DEGREES_CORE_H
#include <stdint.h>
#include "roots.h"

enum { HD_BANKS = 16, HD_PATTERNS = 16, HD_TRACKS = 8, HD_STEPS = 64,
       HD_LOCKS = 8192, HD_LANES = 128, HD_NONE = 255, HD_CODES = 84 };

/* Unpacked runtime layout. Both architectures have no padding because
 * every member is a byte. Native-note snapshots detect edits
 * that arrive through a native path; they are not a second playable sequence. */
typedef struct {
    HdRoots roots[HD_LANES];
} HdBank;
_Static_assert(sizeof(HdBank) == 16768, "Part-owned degree runtime ABI");

extern HdBank hd_banks[HD_BANKS];
extern volatile uint8_t hd_busy[HD_TRACKS];
extern volatile uint8_t hd_target[HD_TRACKS], hd_busy_context[HD_TRACKS];
extern int hd_encode_c(int note, int scale);
extern int hd_decode_c(int degree, int scale);
extern int hd_ui_context_c(void);
extern unsigned hd_follow_c(void);
extern unsigned hd_scales_c(void);
extern unsigned hd_scenes_c(void);
int hd_scene_value_c(unsigned context, unsigned track, unsigned flat, int base);
void hd_scene_before_c(unsigned context);
void hd_scenes_before_c(uintptr_t bank);
void hd_scene_mode_c(unsigned context, unsigned track, unsigned old, unsigned mode, int scale);
void hd_scene_part_byte_c(unsigned context, unsigned offset, unsigned value);
int hd_scene_delta_c(unsigned side, unsigned flat, int delta);
int hd_scene_ui_c(unsigned flat, int base);
extern uintptr_t hd_scene_memory_c(void);
extern void hd_scene_ensure_c(void);
extern void hd_scene_invalidate_c(void);
extern void hd_scene_changed_c(unsigned bank);
extern int hd_play_context_c(unsigned track);
extern int hd_part_read_c(unsigned track, unsigned context, unsigned field);
extern int hd_part_key_c(unsigned track, unsigned context);
extern int hd_part_write_c(unsigned track, unsigned context, unsigned field, unsigned value);
int hd_pattern_context_c(unsigned bank, unsigned pattern);
unsigned hd_part_type_c(unsigned bank, unsigned part, unsigned track);
int hd_sync_c(unsigned bank, unsigned pattern, unsigned track);
void hd_part_before_c(uintptr_t destination);
void hd_checkpoint_c(unsigned bank);
uint32_t hd_revision_c(unsigned bank);
void hd_configuration_changed_c(unsigned bank);
void hd_ui_observe_c(void);
void hd_event_tick_c(unsigned track);
int hd_context_replacing_c(unsigned context, unsigned track);
int hd_context_depends_c(unsigned context, unsigned track, unsigned source_context);
void hd_events_part_before_c(unsigned context);
void hd_record_part_before_c(unsigned context);
int hd_capture_c(unsigned note, unsigned track);
int hd_capture_message_c(uintptr_t message, unsigned note, unsigned track);
void hd_record_modes_c(unsigned track, unsigned mode);
void hd_record_consume_c(uintptr_t message);

void hd_reset_c(void);
void hd_bank_reset_c(unsigned bank);
void hd_bank_loaded_c(unsigned bank);
void hd_ready_all_c(void);
void hd_mode_c(unsigned track, unsigned mode);
int hd_degree_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
int hd_base_c(unsigned bank, unsigned part, unsigned track);
int hd_resolve_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
int hd_scale_c(unsigned bank, unsigned part, unsigned track);
void hd_record_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree);
void hd_record_publish_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree);
void hd_edit_base_c(unsigned bank, unsigned part, unsigned track, int degree);
void hd_edit_step_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree);
int hd_lock_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
void hd_copy_note_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree, int note);
int hd_validate_c(const HdBank *bank);
void hd_events_reset_c(void);
void hd_event_stage_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int slot);
void hd_event_copy_c(unsigned track);
int hd_event_fire_c(unsigned slot, unsigned track);
void hd_events_mode_c(unsigned track, unsigned mode);
int hd_prepare_c(int native_note, unsigned track);
int hd_payload_valid_c(const uint8_t *payload);
uint32_t hd_payload_hash_c(const uint8_t *payload);
int hd_export_c(unsigned bank, uint8_t *payload);
void hd_import_c(unsigned bank, const uint8_t *payload);
uint32_t hd_native_hash_c(unsigned bank, uint32_t hash);
void hd_nv_save_c(unsigned bank);
void hd_nv_dirty_c(unsigned bank);
void hd_nv_poll_c(void);
int hd_nv_restore_c(unsigned bank);
int hd_ui_advance_c(int code, int delta);
int hd_ui_value_c(int step);
int hd_ui_edit_c(int delta, int toggle, int steps);
void hd_copy_before_c(uintptr_t destination, uintptr_t source, unsigned length);
int hd_copy_after_c(void);
void hd_operations_reset_c(void);
void hd_step_copy_c(uintptr_t buffer, unsigned pattern, unsigned track, unsigned page, unsigned mask);
int hd_step_paste_c(uintptr_t buffer, unsigned slot, unsigned pattern, unsigned track, unsigned step);
void hd_forget_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
#endif
