/* Configuration is pattern-owned; the running phase is volatile and never
 * checkpointed. A fired event captures one offset. Arp repeats and pool
 * rebuilds reuse it; only its first actual output advances the next offset. */
#include "accumulator.h"
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define WORD(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define LONG(a) (*(volatile uint32_t *)(uintptr_t)(a))
HaLane ha_lanes[16][128];
typedef struct {
    int8_t offset[64], direction[64];
    unsigned identity;
    uint8_t bank, pattern, step, valid, sounded, restart;
    int8_t captured;
} HaPhase;
static HaPhase phases[8];
static uint16_t mask(void) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tmove.w #0x2700,%%sr" : "=d"(sr) :: "cc", "memory");
    return sr;
}
static void unmask(uint16_t sr) {
    __asm__ volatile("move.w %0,%%sr" :: "d"(sr) : "cc", "memory");
}
static void defaults(HaLane *p) {
    for (unsigned i=0;i<32;++i) p->amount[i]=0;
    p->lower=0; p->upper=7; p->boundary=0; p->reset=3; p->base=1;
}
static void reset(HaPhase *p) {
    for (unsigned i=0;i<64;++i) { p->offset[i]=0; p->direction[i]=1; }
    p->valid=0;
}
void ha_runtime_reset_c(void) {
    for (unsigned t=0;t<8;++t) { reset(&phases[t]); phases[t].identity=~0u; phases[t].restart=0; }
}
void ha_bank_reset_c(unsigned bank) {
    if (bank>=16) return;
    for (unsigned i=0;i<128;++i) defaults(&ha_lanes[bank][i]);
    for (unsigned t=0;t<8;++t) if (phases[t].identity/16==bank) {
        reset(&phases[t]); phases[t].identity=~0u;
    }
}
int ha_amount_c(unsigned code) {
    return code<2 || code>15 ? 0 : code<9 ? (int)code-9 : (int)code-8;
}
unsigned ha_lock_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    if (bank>=16 || pattern>=16 || track>=8 || step>=64) return 0;
    unsigned byte=ha_lanes[bank][pattern*8+track].amount[step/2];
    return (byte >> ((step&1) ? 0 : 4))&15;
}
static void dirty(unsigned bank) {
    hd_configuration_changed_c(bank);
    LONG(0x400e21e0u+bank*0x9b340u+0x9b332)=1;
    if (LONG(0x46c82456)==0x400e21e0u+bank*0x9b340u) LONG(0x100f8598)=1;
}
void ha_set_c(unsigned bank, unsigned pattern, unsigned track, unsigned step, unsigned code) {
    if (bank>=16 || pattern>=16 || track>=8 || step>=64 || code>15) return;
    uint16_t sr=mask();
    dirty(bank);
    unsigned shift=(step&1) ? 0 : 4;
    uint8_t *p=&ha_lanes[bank][pattern*8+track].amount[step/2];
    *p=(uint8_t)((*p & ~(15u<<shift)) | (code<<shift));
    if (phases[track].identity==bank*16+pattern) {
        phases[track].offset[step]=0; phases[track].direction[step]=1;
    }
    unmask(sr);
}
void ha_transport_c(void) {
    /* Both native cold-start and resume edges. Resolve policy on the next
     * actual note event, using its incoming pattern rather than the UI. */
    for (unsigned track=0;track<8;++track) phases[track].restart=1;
}
void ha_settings_copy_c(unsigned bank, unsigned pattern, unsigned track, const HaLane *source) {
    if (bank>=16 || pattern>=16 || track>=8) return;
    uint16_t sr=mask(); dirty(bank);
    HaLane *dst=&ha_lanes[bank][pattern*8+track];
    dst->lower=source->lower;dst->upper=source->upper;dst->boundary=source->boundary;
    dst->reset=source->reset;dst->base=source->base;
    if (phases[track].identity==bank*16+pattern) reset(&phases[track]);
    unmask(sr);
}
void ha_fire_c(unsigned bank, unsigned pattern, unsigned track, unsigned step) {
    if (bank>=16 || pattern>=16 || track>=8 || step>=64) return;
    HaPhase *p=&phases[track];
    const HaLane *c=&ha_lanes[bank][pattern*8+track];
    if (p->restart && (c->reset&1)) reset(p);
    p->restart=0;
    if (p->identity!=bank*16+pattern && (p->identity>=256 || (c->reset&2))) reset(p);
    p->identity=bank*16+pattern; p->bank=(uint8_t)bank;
    p->pattern=(uint8_t)pattern; p->step=(uint8_t)step;
    p->captured=p->offset[step]; p->valid=1; p->sounded=0;
}
int ha_shift_c(int note, unsigned track, unsigned context) {
    if (track>=8 || context>=64 || note<0 || note>127) return note;
    HaPhase *p=&phases[track];
    if (!p->valid) return note;
    const HaLane *c=&ha_lanes[p->bank][p->pattern*8+track];
    unsigned code=ha_lock_c(p->bank,p->pattern,track,p->step);
    if (!code) code=c->base;
    if (!ha_amount_c(code) || !p->captured) return note;
    int scale=hd_scale_c(context/4,context%4,track);
    return hd_decode_c(hd_encode_c(note,scale)+p->captured,scale);
}
void ha_sounded_c(unsigned track) {
    if (track>=8) return;
    HaPhase *p=&phases[track];
    if (!p->valid || p->sounded) return;
    p->sounded=1;
    const HaLane *c=&ha_lanes[p->bank][p->pattern*8+track];
    unsigned code=ha_lock_c(p->bank,p->pattern,track,p->step);
    if (!code) code=c->base;
    int amount=ha_amount_c(code), lo=c->lower, hi=c->upper;
    if (!amount) { p->offset[p->step]=0; p->direction[p->step]=1; return; }
    int next=p->captured+amount*p->direction[p->step];
    if (lo==hi) next=lo;
    else if (next<lo || next>hi) switch(c->boundary) {
        case 0: while (next<lo) next+=hi-lo+1; while (next>hi) next-=hi-lo+1; break;
        case 1:
            while (next<lo || next>hi) {
                if (next>hi) next=2*hi-next; else next=2*lo-next;
                p->direction[p->step]=(int8_t)-p->direction[p->step];
            }
            break;
        case 2: next=next<lo ? lo : hi; break;
        default: next=0; break;
    }
    p->offset[p->step]=(int8_t)next;
}
int ha_valid_c(const volatile uint8_t *p) {
    for (unsigned lane=0;lane<128;++lane,p+=37)
        if ((int8_t)p[32]<-63 || (int8_t)p[32]>0 || p[33]>63 ||
            p[34]>3 || p[35]>3 || p[36]<1 || p[36]>15) return 0;
    return 1;
}
void ha_pack_c(unsigned bank, volatile uint8_t *p) {
    const uint8_t *src=(const uint8_t *)ha_lanes[bank];
    for (unsigned i=0;i<HA_BANK_BYTES;++i) p[i]=src[i];
}
void ha_unpack_c(unsigned bank, const volatile uint8_t *p) {
    uint8_t *dst=(uint8_t *)ha_lanes[bank];
    for (unsigned i=0;i<HA_BANK_BYTES;++i) dst[i]=p[i];
    for (unsigned t=0;t<8;++t) if (phases[t].identity/16==bank) {
        reset(&phases[t]); phases[t].identity=~0u;
    }
}
static int ui(unsigned *bank, unsigned *pattern, unsigned *track) {
    int context=hd_ui_context_c();
    *pattern=BYTE(0x100b14d0); *track=BYTE(0x100b14cc);
    if (context<0 || *pattern>=16 || *track>=8) return 0;
    *bank=(unsigned)context/4;
    return hd_part_type_c(*bank,(unsigned)context%4,*track)!=0;
}
int ha_ui_value_c(int step) {
    unsigned b,p,t;
    if (!ui(&b,&p,&t)) return 1;
    unsigned code=step<0 ? 0 : ha_lock_c(b,p,t,(unsigned)step);
    return code ? (int)code|256 : ha_lanes[b][p*8+t].base;
}
static unsigned advance(unsigned code, int delta) {
    /* Display order -7..-1, OFF, +1..+7; inherit is a lock state only. */
    int v=ha_amount_c(code);
    if (delta>14) delta=14;
    if (delta<-14) delta=-14;
    v+=delta;
    if (v<-7) v=-7;
    if (v>7) v=7;
    return v<0 ? (unsigned)(v+9) : v>0 ? (unsigned)(v+8) : 1;
}
int ha_ui_edit_c(int delta, int toggle, int steps) {
    unsigned b,p,t;
    if (!ui(&b,&p,&t) || (!delta && !toggle)) return 0;
    if (!steps) {
        unsigned next=advance(ha_lanes[b][p*8+t].base,delta);
        if (next==ha_lanes[b][p*8+t].base) return 0;
        uint16_t sr=mask(); dirty(b);
        ha_lanes[b][p*8+t].base=(uint8_t)next;
        if (phases[t].identity==b*16+p) reset(&phases[t]);
        unmask(sr); return 1;
    }
    unsigned held=WORD(0x460d174a), start=LONG(0x460d174c), changed=0;
    for (unsigned i=0;i<16 && start+i<64;++i) if (held & (1u<<i)) {
        unsigned code=ha_lock_c(b,p,t,start+i);
        unsigned next=toggle && code ? 0 : advance(code ? code : ha_lanes[b][p*8+t].base,delta);
        if (next==code) continue;
        ha_set_c(b,p,t,start+i,next); changed=1;
    }
    return (int)changed;
}
int ha_setting_c(unsigned track, unsigned knob, int delta) {
    int context=hd_ui_context_c(); unsigned pattern=BYTE(0x100b14d0);
    if (context<0 || track>=8 || pattern>=16 || knob>=4) return 0;
    unsigned bank=(unsigned)context/4;
    HaLane *c=&ha_lanes[bank][pattern*8+track];
    int old=knob==0 ? c->lower : knob==1 ? c->upper : knob==2 ? c->boundary : c->reset;
    if (!delta) return old;
    if (delta>63) delta=63;
    if (delta<-63) delta=-63;
    int value=old+delta, lo=knob==0 ? -63 : 0, hi=knob==0 ? 0 : knob==1 ? 63 : 3;
    if (value<lo) value=lo;
    if (value>hi) value=hi;
    if (value==old) return old;
    uint16_t sr=mask(); dirty(bank);
    if (!knob) c->lower=(int8_t)value;
    else if (knob==1) c->upper=(int8_t)value;
    else if (knob==2) c->boundary=(uint8_t)value;
    else c->reset=(uint8_t)value;
    if (phases[track].identity==bank*16+pattern) reset(&phases[track]);
    unmask(sr);
    return value;
}
void ha_format_c(char *buffer, int code) {
    int amount=ha_amount_c((unsigned)code);
    if (!amount) { buffer[0]='O';buffer[1]='F';buffer[2]='F';buffer[3]=0; }
    else { buffer[0]=amount<0 ? '-' : '+';buffer[1]=(char)('0'+(amount<0 ? -amount : amount));buffer[2]=0; }
}
