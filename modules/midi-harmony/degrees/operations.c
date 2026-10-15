/* Metadata accompanies native pattern/track clipboard and undo copies.
 * Native Part bytes carry defaults without a parallel clipboard or conversion.
 * The synchronous native memcpy wrapper captures before copying and repairs
 * representation after copying. It never calls back into a UI dispatcher. */
#include "core.h"
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define LONG(a) (*(volatile uint32_t *)(uintptr_t)(a))

typedef struct { uint8_t degree, note; } Copied;
typedef struct { Copied root[512]; unsigned length, valid; } Clipboard;
typedef struct { unsigned kind, bank, pattern, track, buffer; } Location;
enum { UNKNOWN, CLIP, PATTERN, TRACK };
static Clipboard clips[2], transfer;
static Location destination;
static void copy_clip(Clipboard *dst, const Clipboard *src) {
    for (unsigned i = 0; i < 512; ++i) dst->root[i] = src->root[i];
    dst->length = src->length;
    dst->valid = src->valid;
}

static uintptr_t canonical(uintptr_t p) {
    uintptr_t selected = LONG(0x46c82456);
    unsigned current = (unsigned)(selected-0x400e21e0u)/0x9b340;
    if (current < 16) {
        uintptr_t bank = 0x400e21e0u + current*0x9b340;
        if (p >= 0x1001614e && p < 0x1001614e + 0x8ed80)
            p = bank+p-0x1001614e;
        else if (p >= 0x100a4ece && p < 0x100a4ece + 4*0x18b2)
            p = bank+0x8ed80+p-0x100a4ece;
        else if (p >= 0x100ab196 && p < 0x100ab196+4*0x18b2)
            p = bank+0x9504a+p-0x100ab196;
    }
    return p;
}
static Location locate(uintptr_t p, unsigned length) {
    Location l = {0,0,0,0,0};
    if (p == 0x460c8122 || p == 0x460bf218) {
        l.kind = CLIP;
        l.buffer = p == 0x460bf218;
        return l;
    }
    p = canonical(p);
    if (p < 0x400e21e0 || p >= 0x400e21e0 + 16*0x9b340) return l;
    unsigned offset = (unsigned)(p-0x400e21e0);
    l.bank = offset / 0x9b340;
    offset %= 0x9b340;
    l.pattern = offset/0x8ed8;
    offset %= 0x8ed8;
    if (l.pattern >= 16) return l;
    if (length == 0x8ed8 && !offset) l.kind = PATTERN;
    if (length == 0x8b0 && offset >= 0x48d0 && offset < 0x48d0 + 8*0x8b0) {
        offset -= 0x48d0;
        if (!(offset%0x8b0)) { l.kind = TRACK; l.track = offset/0x8b0; }
    }
    return l;
}
static int absolute(int code, int scale) {
    int n = hd_decode_c(code,scale);
    return n >= 0 ? n : code < 7 ? 0 : 127;
}
static Copied capture(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    uintptr_t native = 0x400e21e0u + bank*0x9b340;
    Copied result = {HD_NONE,HD_NONE};
    int context = hd_pattern_context_c(bank,pattern);
    if (context < 0) return result;
    (void)hd_sync_c(bank,pattern,track);
    result.note = BYTE(native+pattern*0x8ed8+0x4900+track*0x8b0+step*32);
    if (hd_part_type_c(bank,(unsigned)context%4,track))
        result.degree = (uint8_t)hd_lock_c(bank,pattern,track,step);
    if (result.note != HD_NONE && result.degree < HD_CODES)
        result.note = (uint8_t)absolute(result.degree,hd_scale_c(bank,(unsigned)context%4,track));
    return result;
}
void hd_copy_before_c(uintptr_t dst, uintptr_t src, unsigned length) {
    transfer.valid = 0;
    if (dst == 0x460c8122 || dst == 0x460bf218) {
        unsigned clip = dst == 0x460bf218;
        if (length != 0x8ed8 && length != 0x8b0) clips[clip].valid = 0;
    }
    if (length != 0x8ed8 && length != 0x8b0) return;
    destination = locate(dst,length);
    Location source = locate(src,length);
    if (!source.kind || !destination.kind) {
        if (destination.kind == CLIP) clips[destination.buffer].valid = 0;
        return;
    }
    if (source.kind == CLIP) {
        if (!clips[source.buffer].valid || clips[source.buffer].length != length) return;
        copy_clip(&transfer,&clips[source.buffer]);
    } else {
        unsigned count = source.kind == PATTERN ? 512 : 64;
        for (unsigned i = 0; i < count; ++i) {
            unsigned track = source.kind == PATTERN ? i/64 : source.track;
            transfer.root[i] = capture(source.bank,source.pattern,track,i%64);
        }
        transfer.valid = 1;
        transfer.length = length;
    }
}
int hd_copy_after_c(void) {
    if (!transfer.valid) return -1;
    if (destination.kind == CLIP) {
        copy_clip(&clips[destination.buffer],&transfer);
        return -1;
    }
    unsigned count = destination.kind == PATTERN ? 512 : 64;
    for (unsigned i = 0; i < count; ++i) {
        unsigned track = destination.kind == PATTERN ? i/64 : destination.track;
        Copied c = transfer.root[i];
        int degree = c.degree < HD_CODES ? c.degree : -1;
        hd_copy_note_c(destination.bank,destination.pattern,track,i%64,degree,c.note);
    }
    return (int)destination.bank;
}
void hd_operations_reset_c(void) {
    clips[0].valid = clips[1].valid = transfer.valid = 0;
}
void hd_step_copy_c(uintptr_t buffer, unsigned pattern, unsigned track, unsigned page, unsigned mask) {
    Location dst = locate(buffer,0);
    if (dst.kind != CLIP || pattern >= 16 || track >= 8 || page >= 4) return;
    unsigned bank = (LONG(0x46c82456)-0x400e21e0u)/0x9b340;
    if (bank >= 16) return;
    Clipboard *c = &clips[dst.buffer];
    c->valid = 1;
    c->length = 0;
    for (unsigned i = 0; i < 16; ++i)
        if (mask & (1u << i)) c->root[i] = capture(bank,pattern,track,page*16+i);
}
int hd_step_paste_c(uintptr_t buffer, unsigned slot, unsigned pattern, unsigned track, unsigned step) {
    Location src = locate(buffer,0);
    if (src.kind != CLIP || slot >= 16 || pattern >= 16 || track >= 8 || step >= 64) return -1;
    Clipboard *c = &clips[src.buffer];
    if (!c->valid || c->length) return -1;
    unsigned bank = (LONG(0x46c82456)-0x400e21e0u)/0x9b340;
    if (bank >= 16) return -1;
    Copied root = c->root[slot];
    hd_copy_note_c(bank,pattern,track,step,root.degree < HD_CODES ? root.degree : -1,root.note);
    return (int)bank;
}
