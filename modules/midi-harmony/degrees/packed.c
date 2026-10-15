/* Fixed-capacity storage: 85 degree states times 9 CHRD states fit 10 bits.
 * HARM publications use a canonical native mirror, so the exact edit
 * snapshot is reconstructed from DEG. Non-HARM snapshots are never used
 * for edit detection. No sparse overflow, journal or capacity reduction.
 * Each lane starts with state*84+scale, followed by MSB-first tokens.
 * Exact snapshots are essential: KEY changes preserve DEG, whereas a native
 * NOTE edit since the checkpoint must be detected, including after reboot. */
#include "packed.h"

static inline int token(const HdRoots *r, unsigned step, unsigned q) {
    unsigned d = r->degree[step];
    if (q > 7 && q != HD_NONE) return -1;
    if (r->state == HD_ROOT_HARM && r->note[step] != hd_mirror_c(d)) return -1;
    return (int)((d == HD_NONE ? 84u : d) * 9u + (q == HD_NONE ? 8u : q));
}

int hd_pack_c(const HdBank *bank, const uint8_t *qualities, volatile uint8_t *p) {
    for (unsigned lane = 0; lane < HD_LANES; ++lane) {
        const HdRoots *r = &bank->roots[lane];
        if (!hd_roots_valid_c(r)) return 0;
        *p++ = (uint8_t)(r->state * 84u + r->scale);
        /* Four ten-bit tokens always occupy five bytes. The format is
         * unchanged; no per-token reservoir or variable shift loop. */
        for (unsigned step = 0; step < HD_STEPS; step += 4) {
            int a = token(r,step,qualities[0]), b = token(r,step+1,qualities[1]);
            int c = token(r,step+2,qualities[2]), d = token(r,step+3,qualities[3]);
            if ((a | b | c | d) < 0) return 0;
            p[0] = (uint8_t)((unsigned)a >> 2);
            p[1] = (uint8_t)(((unsigned)a << 6) | ((unsigned)b >> 4));
            p[2] = (uint8_t)(((unsigned)b << 4) | ((unsigned)c >> 6));
            p[3] = (uint8_t)(((unsigned)c << 2) | ((unsigned)d >> 8));
            p[4] = (uint8_t)d;
            p += 5;
            qualities += 4;
        }
    }
    return 1;
}

/* Null destinations perform the first, read-only validation pass. */
static int decode(HdBank *bank, uint8_t *qualities, const volatile uint8_t *p) {
    for (unsigned lane = 0; lane < HD_LANES; ++lane) {
        unsigned meta = *p++, state = meta / 84, scale = meta % 84;
        if (meta >= 252) return 0;
        HdRoots *r = bank ? &bank->roots[lane] : 0;
        if (r) {
            r->state = (uint8_t)state;
            r->scale = (uint8_t)scale;
            r->context = HD_NONE;
        }
        uint32_t pending = 0;
        unsigned bits = 0;
        for (unsigned step = 0; step < HD_STEPS; ++step) {
            while (bits < 10) {
                pending = (pending << 8) | *p++;
                bits += 8;
            }
            bits -= 10;
            unsigned token = (pending >> bits) & 0x3ffu;
            unsigned d = token / 9, q = token % 9;
            if (d > 84 || (state != HD_ROOT_HARM && d != 84)) return 0;
            if (d == 84) d = HD_NONE;
            if (r) { r->degree[step] = (uint8_t)d; r->note[step] = (uint8_t)hd_mirror_c(d); }
            if (qualities) *qualities++ = (uint8_t)(q == 8 ? HD_NONE : q);
        }
    }
    return 1;
}
int hd_packed_valid_c(const volatile uint8_t *payload) {
    return decode(0, 0, payload);
}
int hd_unpack_c(HdBank *bank, uint8_t *qualities, const volatile uint8_t *payload) {
    if (!hd_packed_valid_c(payload)) return 0;
    return decode(bank, qualities, payload);
}
