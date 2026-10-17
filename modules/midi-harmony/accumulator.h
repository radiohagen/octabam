#ifndef HARMONY_ACCUMULATOR_H
#define HARMONY_ACCUMULATOR_H
#include "core.h"
/* Nibbles: 0 inherit, 1 off, 2..8 negative, 9..15 positive. */
enum { HA_LANE_BYTES = 37, HA_BANK_BYTES = 128 * HA_LANE_BYTES };
typedef struct {
    uint8_t amount[32];
    int8_t lower, upper;
    uint8_t boundary, reset, base;
} HaLane;
_Static_assert(sizeof(HaLane) == HA_LANE_BYTES, "accumulator lane ABI");
extern HaLane ha_lanes[16][128];
int ha_amount_c(unsigned code);
unsigned ha_lock_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
void ha_set_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, unsigned code);
void ha_settings_copy_c(unsigned bank, unsigned pattern, unsigned track, const HaLane *source);
void ha_bank_reset_c(unsigned bank);
void ha_runtime_reset_c(void);
void ha_transport_c(void);
void ha_fire_c(unsigned bank, unsigned pattern, unsigned track, unsigned step);
int ha_shift_c(int note, unsigned track, unsigned context);
void ha_sounded_c(unsigned track);
int ha_valid_c(const volatile uint8_t *p);
void ha_pack_c(unsigned bank, volatile uint8_t *p);
void ha_unpack_c(unsigned bank, const volatile uint8_t *p);
int ha_ui_value_c(int step);
int ha_ui_edit_c(int delta, int toggle, int steps);
int ha_setting_c(unsigned track, unsigned knob, int delta);
void ha_format_c(char *buffer, int code);
#endif
