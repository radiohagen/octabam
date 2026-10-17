/* Pattern-owned degree roots; defaults belong to native Parts. No KITS or files. */
#include "core.h"
#include "accumulator.h"
#define BANK_SIZE 0x9b340u
#define PATTERN_SIZE 0x8ed8u
#define PART_SIZE 0x18b2u
#define WORK_PARTS 0x8ed80u
#define SAVED_PARTS 0x9504au
#define NATIVE_BASE 0x400e21e0u
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define WORD(a) (*(volatile uint32_t *)(uintptr_t)(a))

HdBank hd_banks[HD_BANKS];
volatile uint8_t hd_busy[HD_TRACKS], hd_target[HD_TRACKS], hd_busy_context[HD_TRACKS];
static volatile uint32_t revision[HD_BANKS][HD_LANES], bank_revision[HD_BANKS];
extern volatile uint32_t mp_snapshot_bank, mp_snapshot_parts;
static uint16_t mask(void) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tmove.w #0x2700,%%sr" : "=d"(sr) :: "cc", "memory");
    return sr;
}
static void unmask(uint16_t sr) {
    __asm__ volatile("move.w %0,%%sr" :: "d"(sr) : "cc", "memory");
}
static volatile uint8_t *native(unsigned bank) {
    return (volatile uint8_t *)(uintptr_t)(NATIVE_BASE+BANK_SIZE*bank);
}
static unsigned part_offset(unsigned part) {
    return part < 4 ? WORK_PARTS+part*PART_SIZE : SAVED_PARTS+(part-4)*PART_SIZE;
}
static volatile uint8_t *base_note(unsigned bank, unsigned part, unsigned track) {
    return native(bank)+part_offset(part)+0x3e2 + 32*track;
}
static volatile uint8_t *step_note(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    return native(bank)+pattern*PATTERN_SIZE+0x4900 + track*0x8b0 + step*32;
}
static HdRoots *roots(unsigned bank, unsigned pattern, unsigned track) {
    return &hd_banks[bank].roots[pattern*8+track];
}
static void changed(unsigned bank, unsigned pattern, unsigned track) {
    hd_nv_dirty_c(bank);
    ++revision[bank][pattern*8+track];
    ++bank_revision[bank];
}
uint32_t hd_revision_c(unsigned bank) {
    return bank < HD_BANKS ? bank_revision[bank] : 0;
}
void hd_configuration_changed_c(unsigned bank) {
    if (bank>=HD_BANKS) return;
    hd_nv_dirty_c(bank);
    ++bank_revision[bank];
}
static unsigned scale_id(unsigned scale) {
    return (scale >> 6)*12+((scale >> 2)&15u);
}
int hd_pattern_context_c(unsigned bank, unsigned pattern) {
    if (bank >= 16 || pattern >= 16) return -1;
    unsigned part = native(bank)[pattern*PATTERN_SIZE+0x8e57];
    return part < 4 ? (int)(bank*4+part) : -1;
}
unsigned hd_part_type_c(unsigned bank, unsigned part, unsigned track) {
    if (bank >= 16 || part >= 8 || track >= 8) return 0;
    unsigned mode = part < 4 ? (unsigned)hd_part_read_c(track,bank*4+part,5) :
                    native(bank)[part_offset(part)+0x4e2 + track*36+5];
    return mode <= 2 ? mode : 0;
}
int hd_scale_c(unsigned bank, unsigned part, unsigned track) {
    if (bank >= 16 || part >= 8 || track >= 8) return 0;
    unsigned own_bank = bank, own_part = part, own_track = track, seen = 1u << track;
    if (hd_follow_c()) for (;;) {
        unsigned source = part < 4 ? (unsigned)hd_part_read_c(track,bank*4+part,3) :
                          native(bank)[part_offset(part)+0x4e2 + track*36+3];
        if (!source) break;
        if (source > 8 || (seen & (1u << (source-1)))) {
            bank = own_bank; part = own_part; track = own_track;
            break;
        }
        track = source-1;
        seen |= 1u << track;
        int context = hd_play_context_c(track);
        if (context < 0 || context >= 64) {
            bank = own_bank; part = own_part; track = own_track;
            break;
        }
        bank = (unsigned)context/4;
        part = (unsigned)context%4;
    }
    unsigned raw = part < 4 ? (unsigned)hd_part_key_c(track,bank*4+part) :
                   native(bank)[part_offset(part)+0x4e2 + track*36+17];
    if (!raw || raw > 84) return 0;
    if (raw <= 24) return (int)(((raw-1)/2)*4+((raw-1)&1)*320);
    if (!hd_scales_c()) return 0;
    static const unsigned modes[5] = {1,2,3,4,6};
    return (int)(((raw-25)/5)*4+modes[(raw-25)%5]*64);
}
int hd_context_depends_c(unsigned context, unsigned track, unsigned source_context) {
    if (context >= 64 || track >= 8) return 0;
    unsigned seen = 1u << track;
    for (;;) {
        if (context == source_context) return 1;
        if (!hd_follow_c()) return 0;
        unsigned source = (unsigned)hd_part_read_c(track,context,3);
        if (!source || source > 8 || (seen & (1u << (source-1)))) return 0;
        track = source-1;
        seen |= 1u << track;
        int next = hd_play_context_c(track);
        if (next < 0 || next >= 64) return 0;
        context = (unsigned)next;
    }
}
int hd_context_replacing_c(unsigned context, unsigned track) {
    uintptr_t bank = mp_snapshot_bank;
    if (!bank) return 0;
    unsigned first = (unsigned)(bank-NATIVE_BASE)/BANK_SIZE*4;
    unsigned parts = mp_snapshot_parts;
    for (unsigned part = 0; part < 4; ++part)
        if ((parts & (1u << part)) && hd_context_depends_c(context,track,first+part)) return 1;
    return 0;
}
static void write_native(unsigned bank, volatile uint8_t *p, unsigned value) {
    /* A canonical mirror cannot be interpreted against an older degree
     * checkpoint after a torn publication. Invalidate before the first
     * native store; the UI-task boundary commits the new snapshot. */
    hd_nv_dirty_c(bank);
    *p = (uint8_t)value;
    if (WORD(0x46c82456) != (uintptr_t)native(bank)) return;
    unsigned offset = (unsigned)(p-native(bank));
    if (offset < WORK_PARTS) BYTE(0x1001614e + offset) = (uint8_t)value;
    else if (offset >= WORK_PARTS && offset < WORK_PARTS+4*PART_SIZE)
        BYTE(0x100a4ece + offset-WORK_PARTS) = (uint8_t)value;
    else if (offset >= SAVED_PARTS && offset < SAVED_PARTS+4*PART_SIZE)
        BYTE(0x100ab196 + offset-SAVED_PARTS) = (uint8_t)value;
}
static void dirty(unsigned bank) {
    *(volatile uint32_t *)(native(bank)+0x9b332) = 1;
    if (WORD(0x46c82456) == (uintptr_t)native(bank)) WORD(0x100f8598) = 1;
}
static void part_dirty(unsigned bank, unsigned part) {
    if (part < 4) {
        native(bank)[0x95048] |= (uint8_t)(1u << part);
        if (WORD(0x46c82456) == (uintptr_t)native(bank)) BYTE(0x100b145e) |= (uint8_t)(1u << part);
    }
    dirty(bank);
}
void hd_scene_part_byte_c(unsigned context, unsigned offset, unsigned value) {
    if (context>=64 || offset<0x17a2 || offset>=0x17a2+144 || value>255) return;
    unsigned bank=context/4, part=context%4;
    uint16_t sr=mask();
    write_native(bank,native(bank)+part_offset(part)+offset,value);
    part_dirty(bank,part);
    unmask(sr);
}
static unsigned absolute(unsigned degree, int scale) {
    int note = hd_decode_c((int)degree,scale);
    return note >= 0 ? (unsigned)note : degree < 7 ? 0u : 127u;
}
static void copy_roots(HdRoots *dst, const HdRoots *src) {
    for (unsigned i = 0; i < sizeof(HdRoots); ++i) ((uint8_t *)dst)[i] = ((const uint8_t *)src)[i];
}
static int same_roots(const HdRoots *a, const HdRoots *b) {
    for (unsigned i = 0; i < sizeof(HdRoots); ++i)
        if (((const uint8_t *)a)[i] != ((const uint8_t *)b)[i]) return 0;
    return 1;
}
void hd_bank_reset_c(unsigned bank) {
    if (bank >= 16) return;
    ha_bank_reset_c(bank);
    for (unsigned i = 0; i < HD_LANES; ++i) {
        hd_roots_reset_c(&hd_banks[bank].roots[i]);
        revision[bank][i] = 0;
    }
    ++bank_revision[bank];
}
void hd_reset_c(void) {
    ha_runtime_reset_c();
    for (unsigned bank = 0; bank < 16; ++bank) hd_bank_reset_c(bank);
    for (unsigned track = 0; track < 8; ++track) hd_busy[track] = hd_target[track] = 0;
}
/* Loading bytes does not play every pattern through a reusable Part slot.
 * Imported representation remains authoritative; physical slot indices do not. */
void hd_bank_loaded_c(unsigned bank) {
    if (bank >= 16) return;
    for (unsigned i = 0; i < HD_LANES; ++i) {
        hd_banks[bank].roots[i].context = HD_NONE;
        ++revision[bank][i];
    }
    ++bank_revision[bank];
}
void hd_ready_all_c(void) {
    for (unsigned bank = 0; bank < 16; ++bank) hd_bank_loaded_c(bank);
}
static int sync_context(unsigned bank, unsigned pattern, unsigned track,
                        unsigned context, unsigned mode, unsigned scale) {
    HdRoots *r = roots(bank,pattern,track);
    if (!mode && r->state != HD_ROOT_HARM) return 0;
    if (mode && r->state == HD_ROOT_HARM && r->context == context && r->scale == scale_id(scale)) return 1;
    for (;;) {
        HdRoots next;
        uint8_t notes[64], result[64];
        uint16_t sr = mask();
        uint32_t ticket = revision[bank][pattern*8+track];
        copy_roots(&next,r);
        for (unsigned step = 0; step < 64; ++step) notes[step] = *step_note(bank,pattern,track,step);
        if (next.state == HD_ROOT_HARM && next.context < 64)
            next.scale = (uint8_t)scale_id((unsigned)hd_scale_c(next.context/4,next.context%4,track));
        unmask(sr);
        int edits = hd_roots_sync_c(&next,notes,result,mode,scale,context);
        if (edits < 0) return -1;
        /* An engine interrupt may consume the outgoing snapshot while the
         * native writer is halfway through replacement. It must not attach
         * provenance to the slot the writer is about to publish anew. */
        if (hd_context_replacing_c(context,track)) next.context = HD_NONE;
        /* Detached outgoing contexts are deliberately re-observed during a
         * Part replacement. An identical observation must not invalidate a
         * checkpoint: the higher-priority saver could otherwise keep retrying
         * while the interrupted Part writer never gets to finish. Compare
         * outside the mask; the revision check below also validates this read. */
        int update = edits || !same_roots(r,&next);
        sr = mask();
        unsigned step = 0;
        if (ticket == revision[bank][pattern*8+track])
            while (step < 64 && notes[step] == *step_note(bank,pattern,track,step)) ++step;
        if (step != 64) { unmask(sr); continue; }
        for (step = 0; step < 64; ++step)
            if (notes[step] != result[step]) write_native(bank,step_note(bank,pattern,track,step),result[step]);
        if (update) {
            copy_roots(r,&next);
            changed(bank,pattern,track);
            dirty(bank);
        }
        unmask(sr);
        return mode != 0;
    }
}
int hd_sync_c(unsigned bank, unsigned pattern, unsigned track) {
    if (track >= 8) return -1;
    int context = hd_pattern_context_c(bank,pattern);
    if (context < 0) return -1;
    unsigned part = (unsigned)context%4;
    return sync_context(bank,pattern,track,(unsigned)context,
                        hd_part_type_c(bank,part,track),(unsigned)hd_scale_c(bank,part,track));
}
int hd_base_c(unsigned bank, unsigned part, unsigned track) {
    if (bank >= 16 || part >= 8 || track >= 8) return -1;
    unsigned code = part < 4 ? (unsigned)hd_part_read_c(track,bank*4+part,19) :
                    native(bank)[part_offset(part)+0x4e2 + track*36+19];
    return code < HD_CODES ? (int)code : 35;
}
int hd_lock_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    if (step >= 64 || hd_sync_c(bank,pattern,track) != 1) return -1;
    HdRoots *r = roots(bank,pattern,track);
    uint16_t sr = mask();
    unsigned note = *step_note(bank,pattern,track,step);
    if (note != r->note[step]) {
        int context = hd_pattern_context_c(bank,pattern);
        r->degree[step] = (uint8_t)hd_encode_c((int)note,hd_scale_c(bank,(unsigned)context%4,track));
        r->note[step] = (uint8_t)hd_mirror_c(r->degree[step]);
        write_native(bank,step_note(bank,pattern,track,step),r->note[step]);
        changed(bank,pattern,track);
        dirty(bank);
    }
    unsigned degree = r->degree[step];
    unmask(sr);
    return degree < HD_CODES ? (int)degree : -1;
}
int hd_degree_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    if (step >= 64 || hd_sync_c(bank,pattern,track) != 1) return -1;
    int degree = hd_lock_c(bank,pattern,track,step);
    int context = hd_pattern_context_c(bank,pattern);
    return degree >= 0 ? degree : hd_base_c(bank,(unsigned)context%4,track);
}
int hd_resolve_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    int degree = hd_degree_c(bank,pattern,track,step);
    int context = hd_pattern_context_c(bank,pattern);
    return degree < 0 ? -1 : hd_decode_c(degree,hd_scale_c(bank,(unsigned)context%4,track));
}
/* Shared layer calls this inside its replacement transaction. Capture only
 * attached provenance. Do not encode notes, write Parts or convert inactive
 * patterns here. The composed-image gate must bound this callback's cost. */
void hd_ui_observe_c(void) {
    int context = hd_ui_context_c();
    unsigned pattern = BYTE(0x100b14d0);
    if (context < 0 || hd_pattern_context_c((unsigned)context/4,pattern) != context) return;
    for (unsigned track = 0; track < 8; ++track)
        if (!hd_busy[track]) (void)hd_sync_c((unsigned)context/4,pattern,track);
}
void hd_part_before_c(uintptr_t destination) {
    if (destination >= 0x100a4ece && destination < 0x100a4ece + 4*PART_SIZE) {
        int ui = hd_ui_context_c();
        if (ui < 0) return;
        destination = (uintptr_t)native((unsigned)ui/4)+WORK_PARTS+destination-0x100a4ece;
    }
    if (destination < NATIVE_BASE || destination >= NATIVE_BASE+16*BANK_SIZE) return;
    unsigned offset = (unsigned)(destination-NATIVE_BASE)%BANK_SIZE;
    if (offset < WORK_PARTS || offset >= WORK_PARTS+4*PART_SIZE || (offset-WORK_PARTS)%PART_SIZE) return;
    unsigned replaced = (unsigned)(destination-NATIVE_BASE)/BANK_SIZE*4+(offset-WORK_PARTS)/PART_SIZE;
    /* A second recall may arrive without a trig. Observe the currently
     * selected pattern against the complete outgoing snapshot first. */
    hd_ui_observe_c();
    for (unsigned bank = 0; bank < 16; ++bank) for (unsigned i = 0; i < HD_LANES; ++i) {
        HdRoots *r = &hd_banks[bank].roots[i];
        unsigned context = r->context, track = i%8;
        if (context >= 64 || r->state != HD_ROOT_HARM) continue;
        if (!hd_context_depends_c(context,track,replaced)) continue;
        unsigned scale = (unsigned)hd_scale_c(context/4,context%4,track);
        uint16_t sr = mask();
        if (r->context == context) {
            hd_nv_dirty_c(bank);
            r->scale = (uint8_t)scale_id(scale);
            r->context = HD_NONE;
            ++revision[bank][i];
            ++bank_revision[bank];
        }
        unmask(sr);
    }
    hd_events_part_before_c(replaced);
}
void hd_checkpoint_c(unsigned bank) {
    if (bank >= 16) return;
    for (unsigned i = 0; i < HD_LANES; ++i) {
        HdRoots *r = &hd_banks[bank].roots[i];
        uint16_t sr = mask();
        if (r->state == HD_ROOT_HARM && r->context < 64) {
            r->scale = (uint8_t)scale_id((unsigned)hd_scale_c(r->context/4,r->context%4,i%8));
            ++revision[bank][i];
            ++bank_revision[bank];
        }
        unmask(sr);
    }
}
void hd_mode_c(unsigned track, unsigned mode) {
    int context = hd_ui_context_c();
    if (track >= 8 || mode > 2 || context < 0) return;
    unsigned bank = (unsigned)context/4, part = (unsigned)context%4;
    unsigned old = hd_part_type_c(bank,part,track);
    int scale = hd_scale_c(bank,part,track);
    hd_busy_context[track] = (uint8_t)context;
    hd_target[track] = (uint8_t)mode;
    hd_busy[track] = 1;
    hd_scene_mode_c((unsigned)context,track,old,mode,scale);
    /* Only an explicit HARM edit converts the Part default. Recall carries
     * the incoming Part's own defaults and never calls this setter. */
    if (!old && mode) {
        int degree = hd_encode_c(*base_note(bank,part,track),scale);
        hd_edit_base_c(bank,part,track,degree < 0 ? 35 : degree);
    } else if (old && !mode) {
        uint16_t sr = mask();
        write_native(bank,base_note(bank,part,track),absolute((unsigned)hd_base_c(bank,part,track),scale));
        part_dirty(bank,part);
        unmask(sr);
    }
    unsigned pattern = BYTE(0x100b14d0);
    if (hd_pattern_context_c(bank,pattern) == context)
        (void)sync_context(bank,pattern,track,(unsigned)context,old,(unsigned)scale);
    /* An explicit Part edit crosses the boundary for every pattern still
     * attached to this Part. Detached roots belong to previous occupants of
     * a reused slot and must not be converted by editing the new occupant. */
    for (unsigned p = 0; p < 16; ++p)
        if (roots(bank,p,track)->context == (unsigned)context)
            (void)sync_context(bank,p,track,(unsigned)context,mode,(unsigned)scale);
}
void hd_edit_base_c(unsigned bank, unsigned part, unsigned track, int degree) {
    if (bank >= 16 || part >= 8 || track >= 8 || (unsigned)degree >= HD_CODES) return;
    if (part < 4) { (void)hd_part_write_c(track,bank*4+part,19,(unsigned)degree); return; }
    uint16_t sr = mask();
    write_native(bank,native(bank)+part_offset(part)+0x4e2 + track*36+19,(unsigned)degree);
    dirty(bank);
    unmask(sr);
}
void hd_edit_step_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree) {
    if (step >= 64 || (degree != HD_NONE && (unsigned)degree >= HD_CODES) || hd_sync_c(bank,pattern,track) != 1) return;
    unsigned note = hd_mirror_c((unsigned)degree);
    HdRoots *r = roots(bank,pattern,track);
    uint16_t sr = mask();
    write_native(bank,step_note(bank,pattern,track,step),note);
    r->degree[step] = (uint8_t)degree;
    r->note[step] = (uint8_t)note;
    changed(bank,pattern,track);
    dirty(bank);
    unmask(sr);
}
void hd_record_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree) {
    if (bank >= 16 || pattern >= 16 || track >= 8 || step >= 64) return;
    if (degree >= 128 && degree <= 255) { hd_copy_note_c(bank,pattern,track,step,-1,degree&127); return; }
    if ((unsigned)degree >= HD_CODES || hd_sync_c(bank,pattern,track) != 1) return;
    uint16_t sr = mask();
    hd_record_publish_c(bank,pattern,track,step,degree);
    unmask(sr);
}
/* Native recorder has reconciled the lane before its short publication mask.
 * Never convert a whole lane here: NOTE and its captured degree must publish
 * together, but first-use conversion belongs to the interruptible prepare.
 * Part mode edits/copies and recording run in the UI task; an engine
 * interrupt may change a Follow source's KEY, not this lane's representation. */
void hd_record_publish_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree) {
    if (bank >= 16 || pattern >= 16 || track >= 8 || step >= 64) return;
    HdRoots *r = roots(bank,pattern,track);
    if (degree >= 128 && degree <= 255) {
        unsigned note = (unsigned)degree&127;
        write_native(bank,step_note(bank,pattern,track,step),note);
        if (r->state == HD_ROOT_HARM) {
            int context = hd_pattern_context_c(bank,pattern);
            if (context < 0) return;
            degree = hd_encode_c((int)note,hd_scale_c(bank,(unsigned)context%4,track));
        } else {
            if (r->state != HD_ROOT_UNKNOWN) { r->degree[step] = HD_NONE; r->note[step] = (uint8_t)note; }
            changed(bank,pattern,track);
            dirty(bank);
            return;
        }
    }
    if ((unsigned)degree >= HD_CODES || r->state != HD_ROOT_HARM) return;
    r->degree[step] = (uint8_t)degree;
    r->note[step] = (uint8_t)hd_mirror_c((unsigned)degree);
    write_native(bank,step_note(bank,pattern,track,step),r->note[step]);
    changed(bank,pattern,track);
    dirty(bank);
}
void hd_copy_note_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, int degree, int note) {
    if (bank >= 16 || pattern >= 16 || track >= 8 || step >= 64 || (note != HD_NONE && (unsigned)note > 127)) return;
    int context = hd_pattern_context_c(bank,pattern);
    if (context < 0) return;
    if (hd_part_type_c(bank,(unsigned)context%4,track)) {
        if (note == HD_NONE) degree = HD_NONE;
        else if (degree < 0) degree = hd_encode_c(note,hd_scale_c(bank,(unsigned)context%4,track));
        hd_edit_step_c(bank,pattern,track,step,degree);
    } else {
        (void)hd_sync_c(bank,pattern,track);
        HdRoots *r = roots(bank,pattern,track);
        uint16_t sr = mask();
        write_native(bank,step_note(bank,pattern,track,step),(unsigned)note);
        if (r->state != HD_ROOT_UNKNOWN) { r->degree[step] = HD_NONE; r->note[step] = (uint8_t)note; }
        changed(bank,pattern,track);
        dirty(bank);
        unmask(sr);
    }
}
int hd_validate_c(const HdBank *bank) {
    for (unsigned i = 0; i < HD_LANES; ++i) if (!hd_roots_valid_c(&bank->roots[i])) return 0;
    return 1;
}
void hd_forget_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    if (bank >= 16 || pattern >= 16 || track >= 8 || step >= 64) return;
    ha_set_c(bank,pattern,track,step,0);
    HdRoots *r = roots(bank,pattern,track);
    int context = hd_pattern_context_c(bank,pattern);
    unsigned active = context >= 0 && hd_part_type_c(bank,(unsigned)context%4,track);
    uint16_t sr = mask();
    if (active && r->state == HD_ROOT_HARM) write_native(bank,step_note(bank,pattern,track,step),HD_NONE);
    r->degree[step] = r->note[step] = HD_NONE;
    changed(bank,pattern,track);
    unmask(sr);
}
