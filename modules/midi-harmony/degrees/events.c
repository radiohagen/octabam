/* Degree provenance follows each native staged/pending event. Its captured
 * Part context is independent of UI navigation and later pattern assignment.
 * Only runtime provenance is stored here; defaults remain native Part bytes. */
#include "core.h"

typedef struct {
    uint8_t context, degree, note, active, valid, converted, inherited, attached;
    uint16_t scale;
    int16_t output;
} HdEvent;
static HdEvent staged[8], pending[32], fired[8];
volatile uint8_t hd_rebuild[8];
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))

static uint16_t mask(void) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tmove.w #0x2700,%%sr" : "=d"(sr) :: "cc", "memory");
    return sr;
}
static void unmask(uint16_t sr) {
    __asm__ volatile("move.w %0,%%sr" :: "d"(sr) : "cc", "memory");
}
static unsigned absolute(unsigned degree, unsigned scale) {
    int note = hd_decode_c((int)degree,(int)scale);
    return note >= 0 ? (unsigned)note : degree < 7 ? 0u : 127u;
}
static unsigned native_base(unsigned context, unsigned track) {
    return BYTE(0x400e21e0u + (context/4)*0x9b340u + 0x8ed80 +
                (context%4)*0x18b2 + 0x3e2 + track*32);
}
/* Caller serializes one event. A detached event retains its outgoing scale
 * until it observes an incoming mode, including same-slot replacement. */
static void convert(HdEvent *e, unsigned track, unsigned mode) {
    if (!e->valid) return;
    unsigned scale = (unsigned)hd_scale_c(e->context/4,e->context%4,track);
    if (e->attached) e->scale = (uint16_t)scale;
    if (e->active != (mode != 0)) {
        if (mode) e->degree = e->inherited ? HD_NONE : (uint8_t)hd_encode_c(e->note,(int)scale);
        else e->note = (uint8_t)(e->inherited ? native_base(e->context,track) : absolute(e->degree,e->scale));
        e->active = mode != 0;
        e->converted = 1;
    }
    e->scale = (uint16_t)scale;
    e->attached = !hd_context_replacing_c(e->context,track);
}
void hd_events_reset_c(void) {
    for (unsigned i = 0; i < 8; ++i) staged[i].valid = fired[i].valid = hd_rebuild[i] = 0;
    for (unsigned i = 0; i < 32; ++i) pending[i].valid = 0;
}
void hd_event_stage_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int slot) {
    if (bank >= 16 || pattern >= 16 || track >= 8 || step >= 64 || slot < -1 || slot > 3) return;
    int context = hd_pattern_context_c(bank,pattern);
    if (context < 0) return;
    unsigned active = hd_sync_c(bank,pattern,track) == 1;
    uintptr_t native = 0x400e21e0u + bank*0x9b340u;
    unsigned note = BYTE(native + pattern*0x8ed8 + 0x4900 + track*0x8b0 + step*32);
    HdEvent next = {0};
    next.context = (uint8_t)context;
    next.inherited = note == HD_NONE;
    next.note = (uint8_t)(next.inherited ? native_base((unsigned)context,track) : note);
    next.active = (uint8_t)active;
    next.degree = active ? (uint8_t)hd_lock_c(bank,pattern,track,step) : HD_NONE;
    next.scale = (uint16_t)hd_scale_c(bank,(unsigned)context%4,track);
    next.attached = !hd_context_replacing_c((unsigned)context,track);
    next.output = (int16_t)next.note;
    next.valid = 1;
    if (hd_busy[track] && hd_busy_context[track] == (unsigned)context)
        convert(&next,track,hd_target[track]);
    uint16_t sr = mask();
    *(slot < 0 ? &staged[track] : &pending[(unsigned)slot*8+track]) = next;
    unmask(sr);
}
void hd_event_copy_c(unsigned track) {
    if (track >= 8) return;
    uint16_t sr = mask();
    pending[track] = staged[track];
    unmask(sr);
}
int hd_event_fire_c(unsigned slot, unsigned track) {
    if (slot >= 32 || track >= 8) return -1;
    uint16_t sr = mask();
    fired[track] = pending[slot];
    HdEvent *e = &fired[track];
    if (e->valid) convert(e,track,hd_part_type_c(e->context/4,e->context%4,track));
    int note = e->valid && e->converted && !e->active ? e->note : -1;
    unmask(sr);
    return note;
}
static void mode_one(HdEvent *e, unsigned track, unsigned context, unsigned mode) {
    uint16_t sr = mask();
    if (e->valid && e->context == context) convert(e,track,mode);
    unmask(sr);
}
void hd_events_mode_c(unsigned track, unsigned mode) {
    int context = hd_ui_context_c();
    if (track >= 8 || mode > 2 || context < 0) return;
    mode_one(&staged[track],track,(unsigned)context,mode);
    for (unsigned slot = 0; slot < 4; ++slot) mode_one(&pending[slot*8+track],track,(unsigned)context,mode);
    mode_one(&fired[track],track,(unsigned)context,mode);
    uint16_t sr = mask();
    if (fired[track].valid && fired[track].context == (unsigned)context) {
        hd_rebuild[track] = 1;
        if (!mode) BYTE(0x46c76fe0u + track*32) = fired[track].note;
    }
    unmask(sr);
}
static void detach(HdEvent *e, unsigned track, unsigned context) {
    uint16_t sr = mask();
    if (e->valid && e->attached && hd_context_depends_c(e->context,track,context)) {
        e->scale = (uint16_t)hd_scale_c(e->context/4,e->context%4,track);
        e->attached = 0;
    }
    unmask(sr);
}
void hd_events_part_before_c(unsigned context) {
    hd_record_part_before_c(context);
    for (unsigned track = 0; track < 8; ++track) {
        detach(&staged[track],track,context);
        detach(&fired[track],track,context);
        for (unsigned slot = 0; slot < 4; ++slot) detach(&pending[slot*8+track],track,context);
    }
}
int hd_prepare_c(int note, unsigned track) {
    if (track >= 8) return note;
    HdEvent *e = &fired[track];
    int context = e->valid ? e->context : hd_play_context_c(track);
    if (context < 0) return note;
    if (hd_busy[track] && hd_busy_context[track] == (unsigned)context) return -1;
    unsigned mode = hd_part_type_c((unsigned)context/4,(unsigned)context%4,track);
    if (e->valid) {
        uint16_t sr = mask();
        unsigned old = e->active;
        convert(e,track,mode);
        if (old != e->active) hd_rebuild[track] = 1;
        int result = !mode ? (e->converted ? hd_scene_value_c(e->context,track,0,e->note) : note) : hd_decode_c(
            hd_scene_value_c(e->context,track,0,
                e->inherited ? hd_base_c(e->context/4,e->context%4,track) : e->degree),e->scale);
        e->output = (int16_t)result;
        unmask(sr);
        return result;
    }
    /* No scheduled event yet: inherit the engine Part, never the selected UI. */
    return !mode ? note : hd_decode_c(hd_scene_value_c((unsigned)context,track,0,
                                      hd_base_c((unsigned)context/4,(unsigned)context%4,track)),
                                      hd_scale_c((unsigned)context/4,(unsigned)context%4,track));
}

/* Native engine iteration, including a sustained arp without a new trig.
 * A completed Part switch adopts the engine context; a not-yet-fired queued
 * event retains its own separately captured context. */
void hd_event_tick_c(unsigned track) {
    if (track >= 8 || !fired[track].valid) return;
    int context = hd_play_context_c(track);
    if (context < 0 || (hd_busy[track] && hd_busy_context[track] == (unsigned)context)) return;
    HdEvent *e = &fired[track];
    uint16_t sr = mask();
    if (e->context != (unsigned)context) {
        if (e->attached) e->scale = (uint16_t)hd_scale_c(e->context/4,e->context%4,track);
        e->attached = 0;
        e->context = (uint8_t)context;
        hd_rebuild[track] = 1;
    }
    unsigned mode = hd_part_type_c(e->context/4,e->context%4,track);
    unsigned old = e->active;
    convert(e,track,mode);
    int output = !mode ? (e->converted ? hd_scene_value_c(e->context,track,0,e->note) : e->output) : hd_decode_c(
        hd_scene_value_c(e->context,track,0,
            e->inherited ? hd_base_c(e->context/4,e->context%4,track) : e->degree),e->scale);
    if (old != e->active || e->output != output) {
        e->output = (int16_t)output;
        hd_rebuild[track] = 1;
    }
    if (!mode && e->converted) BYTE(0x46c76fe0u + track*32) = (uint8_t)output;
    unmask(sr);
}
