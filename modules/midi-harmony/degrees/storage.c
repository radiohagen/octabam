/* One validated payload for roots and chord quality. The native bank is
 * still native. Its companion has an independent identity and no legacy
 * migration. The retained copy commits its magic last, under a short mask. */
#include "packed.h"
#ifdef HD_TRACK_SRAM
#include "track-retention.h"
/* Outer saver owns this staging buffer; retained reads occur during load. */
static uint8_t track_payload[HD_PAYLOAD_BYTES];
#endif

enum { QUALITY_BYTES = HD_LOCKS, PAYLOAD_BYTES = HD_PAYLOAD_BYTES };
extern uint8_t ch_lock_table[16 * QUALITY_BYTES];
extern uint8_t ch_lock_status[16];
extern volatile uint32_t ch_nv_bank;
/* Initialized data: the loader's BSS may still contain staging bytes. */
static volatile uint32_t generation = 1, available = 1;
static volatile uint32_t pending = 1;
#define NV ((volatile uint32_t *)hd_nv_base)
extern uint32_t hd_nv_base[];
#define NV_PAYLOAD ((volatile uint8_t *)(NV+8))
#define MAGIC 0x48444e33u

static void invalidate(void) {
#ifdef HD_TRACK_SRAM
    hd_track_invalidate_c();
#else
    NV[0] = 0;
#endif
}

static uint16_t mask(void) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tmove.w #0x2700,%%sr" : "=d"(sr) :: "memory");
    return sr;
}
static void unmask(uint16_t sr) {
    __asm__ volatile("move.w %0,%%sr" :: "d"(sr) : "memory");
}
static uint32_t hash(const volatile uint8_t *p, unsigned n, uint32_t h) {
    while (n--) h = (h ^ *p++) * 0x01000193u;
    return h;
}
/* Called inside a root publication mask, before native NOTE changes.
 * The old checkpoint must never mistake a new canonical mirror for a
 * physical NOTE edit. Bulk copying is deferred to the UI task. */
void hd_nv_dirty_c(unsigned bank) {
    if (bank >= HD_BANKS || ch_nv_bank != bank) return;
    invalidate();
    ++generation;
    pending = 1;
}
void hd_nv_poll_c(void) {
    /* A UI poll is not a new edit. Re-requesting an in-flight save here
     * increments its generation forever when encoding spans a UI tick.
     * Actual edits still invalidate/increment; the outer writer retries. */
    if (pending && available && ch_nv_bank < HD_BANKS) hd_nv_save_c(ch_nv_bank);
}
int hd_payload_valid_c(const uint8_t *p) {
    return hd_packed_valid_c(p);
}
uint32_t hd_payload_hash_c(const uint8_t *p) {
    return hash(p, PAYLOAD_BYTES, 0x811c9dc5u);
}
int hd_export_c(unsigned bank, uint8_t *p) {
    if (bank >= 16) return 0;
    hd_checkpoint_c(bank);
    uint32_t ticket, roots_ticket;
    int valid;
    do {
        ticket = generation;
        roots_ticket = hd_revision_c(bank);
        valid = hd_pack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, p);
    } while (ticket != generation || roots_ticket != hd_revision_c(bank));
    return valid;
}
void hd_import_c(unsigned bank, const uint8_t *p) {
    if (bank >= 16 || !hd_unpack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, p)) return;
    hd_bank_loaded_c(bank);
}
uint32_t hd_native_hash_c(unsigned bank, uint32_t h) {
    if (bank >= 16) return 0;
    /* The caller fingerprints pattern NOTE/trig data. Reassigning a Part
     * slot or changing its defaults must not invalidate explicit locks. */
    return h;
}
void hd_nv_save_c(unsigned bank) {
    if (bank >= 16) return;
    hd_checkpoint_c(bank);
    uint16_t sr = mask();
    ch_nv_bank = bank;
    ++generation;
    /* Only the outer writer owns SRAM. A preempting save requests a retry
     * instead of committing a snapshot the interrupted writer could damage. */
    if (!available) { unmask(sr); return; }
    available = 0;
    invalidate();
    unmask(sr);
    for (;;) {
        uint32_t ticket = generation;
        bank = ch_nv_bank;
        uint32_t roots_ticket = hd_revision_c(bank);
#ifdef HD_TRACK_SRAM
        int valid = hd_pack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, track_payload);
        if (valid) valid = hd_track_write_c(track_payload, bank, ticket, ch_lock_status[bank]);
#else
        int valid = hd_pack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, NV_PAYLOAD);
        uint32_t sum = valid ? hash(NV_PAYLOAD, PAYLOAD_BYTES, 0x811c9dc5u) : 0;
#endif
        sr = mask();
        if (ticket == generation && roots_ticket == hd_revision_c(bank)) {
            if (!valid) { available = 1; unmask(sr); return; }
#ifdef HD_TRACK_SRAM
            hd_track_commit_c();
#else
            NV[1] = HD_STORAGE_VERSION;
            NV[2] = bank;
            NV[3] = PAYLOAD_BYTES;
            NV[4] = sum;
            NV[5] = ticket;
            NV[6] = ch_lock_status[bank];
            NV[7] = ~NV[6];
            NV[0] = MAGIC;
#endif
            pending = 0;
            available = 1;
            unmask(sr);
            return;
        }
        unmask(sr);
    }
}
#ifndef HD_TRACK_SRAM
static int restore_at(unsigned bank, const volatile uint32_t *nv) {
    const volatile uint8_t *payload=(const volatile uint8_t *)(nv+8);
    if (bank >= 16 || nv[0] != MAGIC || nv[1] != HD_STORAGE_VERSION || nv[2] != bank ||
        nv[3] != PAYLOAD_BYTES || nv[6] > 4 || nv[7] != ~nv[6] ||
        nv[4] != hash(payload, PAYLOAD_BYTES, 0x811c9dc5u) ||
        !hd_unpack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, payload)) return 0;
    ch_lock_status[bank] = (uint8_t)nv[6];
    ch_nv_bank = bank;
    hd_bank_loaded_c(bank);
    return 1;
}

#endif
int hd_nv_restore_c(unsigned bank) {
#ifdef HD_TRACK_SRAM
    unsigned status;
    if (!hd_track_read_c(track_payload, bank, &status) ||
        !hd_unpack_c(&hd_banks[bank], ch_lock_table + bank*QUALITY_BYTES, track_payload)) return 0;
    ch_lock_status[bank] = (uint8_t)status;
    ch_nv_bank = bank;
    hd_bank_loaded_c(bank);
    return 1;
#else
    if (restore_at(bank,NV)) return 1;
    /* Migrate the validated H8 checkpoint before the new Scenes writer can
     * reuse its old tail. The working/saved companion format stays HDP3. */
    if ((uintptr_t)NV != 0x100fd560u &&
        *(const volatile uint32_t *)(uintptr_t)0x100fbdf0u != 0x53435331u &&
        restore_at(bank,(const volatile uint32_t *)(uintptr_t)0x100fd560u)) {
        hd_nv_save_c(bank);
        /* Retire the old checkpoint only after the new one is committed.
         * A later invalidated checkpoint must not revive pre-migration edits. */
        if (NV[0] == MAGIC) *(volatile uint32_t *)(uintptr_t)0x100fd560u = 0;
        return 1;
    }
    return 0;
#endif
}
