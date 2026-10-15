/* HMT1, retained current bank only. Each step owns its ten-bit DEG/CHRD
 * token. Steps 1..22 carry a 16-byte lane header in their upper six bits:
 * version, bank, lane, state/scale, status, zero[3], generation, checksum.
 * Step 0's upper six bits are the lane commit marker. Other upper bits
 * are zero. Lane 0 is the bank commit: publish it last, in one aligned
 * word store, only after the outer saver rechecks the runtime generation.
 * Every lane must validate before ANY runtime data is imported. Old
 * contiguous checkpoints are deliberately not read or migrated here.
 */
#include "track-retention.h"
#define MARK 0xac00u
#define TOKEN 0x03ffu

static volatile uint16_t *at(unsigned lane, unsigned step) {
    return (volatile uint16_t *)(uintptr_t)(0x1001614eu + (lane / 8u)*0x8ed8u +
        0x4900u + (lane % 8u)*0x8b0u + step*32u + 30u);
}
static void put32(uint8_t *p, uint32_t v) {
    p[0]=(uint8_t)(v>>24); p[1]=(uint8_t)(v>>16);
    p[2]=(uint8_t)(v>>8); p[3]=(uint8_t)v;
}
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0]<<24 | (uint32_t)p[1]<<16 | (uint32_t)p[2]<<8 | p[3];
}
static uint32_t hash(const uint8_t *p, unsigned n, uint32_t h) {
    while (n--) h=(h ^ *p++)*0x01000193u;
    return h;
}
/* Bit positions are MSB first; the final header group is zero padded. */
static unsigned bits(const uint8_t *p, unsigned pos, unsigned n, unsigned limit) {
    unsigned v=0;
    while (n--) {
        v <<= 1;
        if (pos < limit) v |= (p[pos/8] >> (7-pos%8)) & 1u;
        ++pos;
    }
    return v;
}
static void append(uint8_t *p, unsigned pos, unsigned n, unsigned v, unsigned limit) {
    while (n--) {
        if (pos < limit) p[pos/8] |= (uint8_t)(((v >> n)&1u) << (7-pos%8));
        ++pos;
    }
}
void hd_track_invalidate_c(void) {
    *at(0,0) &= TOKEN;
}
int hd_track_write_c(const uint8_t *payload, unsigned bank, uint32_t ticket, unsigned status) {
    if (bank >= HD_BANKS || status > 4 || !hd_packed_valid_c(payload)) return 0;
    for (unsigned lane=0; lane<HD_LANES; ++lane) {
        const uint8_t *p=payload+lane*HD_PACKED_LANE;
        uint8_t h[16]={1,(uint8_t)bank,(uint8_t)lane,p[0],(uint8_t)status,0,0,0};
        put32(h+8,ticket);
        put32(h+12,hash(p,HD_PACKED_LANE,hash(h,12,0x811c9dc5u)));
        for (unsigned step=0; step<HD_STEPS; ++step) {
            unsigned token=bits(p+1,step*10,10,640);
            unsigned meta=step ? bits(h,(step-1)*6,6,128) : 0;
            *at(lane,step)=(uint16_t)(token | (meta<<10));
        }
        if (lane) *at(lane,0) |= MARK;
    }
    return 1;
}
void hd_track_commit_c(void) {
    *at(0,0) |= MARK;
}
int hd_track_read_c(uint8_t *payload, unsigned bank, unsigned *status) {
    if (bank >= HD_BANKS || (*at(0,0) & ~TOKEN) != MARK) return 0;
    uint32_t generation=0;
    unsigned bank_status=0;
    for (unsigned lane=0; lane<HD_LANES; ++lane) {
        uint8_t h[16]={0};
        uint8_t *p=payload+lane*HD_PACKED_LANE;
        for (unsigned i=0; i<HD_PACKED_LANE; ++i) p[i]=0;
        for (unsigned step=0; step<HD_STEPS; ++step) {
            unsigned word=*at(lane,step), meta=word>>10;
            if (!step) { if ((word & ~TOKEN) != MARK) return 0; }
            else {
                if ((step == 22 && (meta & 15u)) || (step > 22 && meta)) return 0;
                append(h,(step-1)*6,6,meta,128);
            }
            append(p+1,step*10,10,word & TOKEN,640);
        }
        p[0]=h[3];
        if (h[0]!=1 || h[1]!=bank || h[2]!=lane || h[4]>4 || h[5] || h[6] || h[7] ||
            get32(h+12)!=hash(p,HD_PACKED_LANE,hash(h,12,0x811c9dc5u))) return 0;
        if (!lane) { generation=get32(h+8); bank_status=h[4]; }
        else if (get32(h+8)!=generation || h[4]!=bank_status) return 0;
    }
    if (!hd_packed_valid_c(payload)) return 0;
    *status=bank_status;
    return 1;
}
