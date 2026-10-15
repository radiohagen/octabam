/* NOTE-page degree values and edits. The panel wrappers own native redraw,
 * lock-indicator and trigless-lock lifecycle calls. */
#include "core.h"
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define WORD(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define LONG(a) (*(volatile uint32_t *)(uintptr_t)(a))

int hd_ui_value_c(int step) {
    int context = hd_ui_context_c();
    if (context < 0) return -1;
    unsigned bank = (unsigned)context/4, part = (unsigned)context%4;
    unsigned pattern = BYTE(0x100b14d0), track = BYTE(0x100b14cc);
    if (step < 0) return hd_scene_ui_c(0,hd_base_c(bank,part,track));
    int lock = hd_lock_c(bank,pattern,track,(unsigned)step);
    return lock >= 0 ? lock | 256 : hd_degree_c(bank,pattern,track,(unsigned)step);
}
int hd_ui_advance_c(int code, int delta) {
    if (code < 0 || code >= HD_CODES) code = 35; /* sensible editable fallback: 1:3 */
    if (delta > 83) delta = 83;
    if (delta < -83) delta = -83;
    /* FUNC changes the tonic octave, preserving degree even at the bounds. */
    if (BYTE(0x46100b1d) & 0x20) {
        int octave = code/7 + delta;
        if (octave < 0) octave = 0;
        if (octave > 11) octave = 11;
        return octave*7 + code%7;
    }
    code += delta;
    return code < 0 ? 0 : code >= HD_CODES ? HD_CODES-1 : code;
}
int hd_ui_edit_c(int delta, int toggle, int steps) {
    int context = hd_ui_context_c();
    if (context < 0) return 0;
    unsigned bank = (unsigned)context/4, part = (unsigned)context%4;
    unsigned pattern = BYTE(0x100b14d0), track = BYTE(0x100b14cc);
    if (track >= 8 || !hd_part_type_c(bank,part,track) || (!delta && !toggle)) return 0;
    if (!steps) {
        hd_edit_base_c(bank,part,track,hd_ui_advance_c(hd_base_c(bank,part,track),delta));
        return 1;
    }
    unsigned mask = WORD(0x460d174a), start = LONG(0x460d174c), changed = 0;
    for (unsigned i = 0; i < 16; ++i) {
        unsigned step = start+i;
        if (!(mask & (1u << i)) || step >= 64) continue;
        int code = hd_degree_c(bank,pattern,track,step);
        if (toggle && hd_lock_c(bank,pattern,track,step) >= 0) code = HD_NONE;
        else code = hd_ui_advance_c(code,delta);
        hd_edit_step_c(bank,pattern,track,step,code);
        changed = 1;
    }
    return (int)changed;
}
