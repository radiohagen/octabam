/* Degree semantics over unchanged upstream MIDI SCENES full tables.
 * Our adapter owns only NOTE interpretation and the degree display.
 */
#include "core.h"
#define BYTE(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define LONG(a) (*(volatile uint32_t *)(uintptr_t)(a))
typedef struct { uint8_t assigned[2], roots[16*8]; } HdSceneSnapshot;
static HdSceneSnapshot outgoing[64];
extern volatile uint32_t mp_snapshot_bank, mp_snapshot_parts;

static uintptr_t part(unsigned context) {
    return 0x400e21e0u+(context/4)*0x9b340u+0x8ed80u+(context%4)*0x18b2u;
}
static volatile uint8_t *table(unsigned context) {
    hd_scene_ensure_c();
    return (volatile uint8_t *)(hd_scene_memory_c()+context*4096u);
}
void hd_scene_before_c(unsigned context) {
    if (!hd_scenes_c() || context>=64) return;
    uintptr_t p=part(context);
    const volatile uint8_t *slots=table(context);
    for (unsigned i=0;i<2;++i) outgoing[context].assigned[i]=BYTE(p+0x10+i);
    for (unsigned i=0;i<128;++i) outgoing[context].roots[i]=slots[i*32];
}
void hd_scenes_before_c(uintptr_t bank) {
    if (!hd_scenes_c() || bank<0x400e21e0u) return;
    unsigned offset=(unsigned)(bank-0x400e21e0u);
    if (offset>=16u*0x9b340u || offset%0x9b340u) return;
    unsigned context=(offset/0x9b340u)*4;
    for (unsigned i=0;i<4;++i) hd_scene_before_c(context+i);
}
int hd_scene_value_c(unsigned context, unsigned track, unsigned flat, int base) {
    if (!hd_scenes_c() || context>=64 || track>=8 || flat!=0) return base;
    const volatile uint8_t *assigned=(const volatile uint8_t *)(part(context)+0x10);
    int snapshot=mp_snapshot_bank==0x400e21e0u+(context/4)*0x9b340u &&
        (mp_snapshot_parts & (1u<<(context%4)));
    if (snapshot) assigned=outgoing[context].assigned;
    unsigned a=assigned[0],b=assigned[1];
    const volatile uint8_t *slots=table(context);
    unsigned va=a==255 ? 255u : snapshot ? outgoing[context].roots[(a&15u)*8+track] : slots[(a&15u)*256+track*32];
    unsigned vb=b==255 ? 255u : snapshot ? outgoing[context].roots[(b&15u)*8+track] : slots[(b&15u)*256+track*32];
    unsigned maximum=hd_part_type_c(context/4,context%4,track) ? 83u : 127u;
    int left=va<=maximum ? (int)va : base;
    int right=vb<=maximum ? (int)vb : base;
    unsigned weight=127u-(LONG(0x460d16c8)&127u);
    if (!weight) return left;
    if (weight==127) return right;
    return left+(((right-left)*(int)weight)>>7);
}
void hd_scene_mode_c(unsigned context, unsigned track, unsigned old, unsigned mode, int scale) {
    if (!hd_scenes_c() || context>=64 || track>=8 || (!old==!mode)) return;
    volatile uint8_t *slots=table(context);
    unsigned changed=0;
    for (unsigned scene=0;scene<16;++scene) {
        unsigned index=scene*256+track*32,value=slots[index];
        if (value>127) continue;
        int next;
        if (mode) next=hd_encode_c((int)value,scale);
        else {
            if (value>=84) continue;
            next=hd_decode_c((int)value,scale);
            if (next<0) next=value<7 ? 0 : 127;
        }
        if (next>=0 && (unsigned)next!=value) { slots[index]=(uint8_t)next;changed=1; }
    }
    if (changed) hd_scene_changed_c(context/4);
}

/* Native scene hold dispatch supplies its ordinary encoder delta.
 * Seed a missing DEG lock from the Part DEG, not its dormant native NOTE;
 * upstream still performs the write, pack, dirty marking, morph and redraw. */
int hd_scene_delta_c(unsigned side, unsigned flat, int delta) {
    if (!hd_scenes_c() || side>1 || !delta || !LONG(0x80000012) || LONG(0x460d1684)) return delta;
    int context=hd_ui_context_c();
    unsigned track=BYTE(0x100b14cc);
    if (context<0 || track>=8 || !hd_part_type_c((unsigned)context/4,(unsigned)context%4,track)) return delta;
    /* CHRD has its own Part/pattern store. Dormant native NOT2-4 are not
     * CHRD scene endpoints; do not create misleading locks on those knobs. */
    if (flat>=3 && flat<=5) return (-2147483647-1);
    if (flat) return delta;
    unsigned scene=BYTE(part((unsigned)context)+0x10+side);
    if (scene==255) return delta;
    hd_scene_ensure_c();
    volatile uint8_t *slot=(volatile uint8_t *)(hd_scene_memory_c()+(unsigned)context*4096u+(scene&15u)*256+track*32);
    unsigned value=*slot;
    if (value==255) { value=(unsigned)hd_base_c((unsigned)context/4,(unsigned)context%4,track); *slot=(uint8_t)value; }
    int next=hd_ui_advance_c((int)value,delta);
    return next-(int)value;
}

int hd_scene_ui_c(unsigned flat, int base) {
    if (!hd_scenes_c() || flat) return base;
    unsigned side=LONG(0x460d169c), track=BYTE(0x100b14cc);
    int context=hd_ui_context_c();
    if ((side!=1 && side!=2) || context<0 || track>=8) return base;
    unsigned scene=BYTE(part((unsigned)context)+0x10+side-1);
    if (scene==255) return base;
    hd_scene_ensure_c();
    unsigned value=BYTE(hd_scene_memory_c()+(unsigned)context*4096u+(scene&15u)*256+track*32);
    return value<84 ? (int)value|256 : base;
}
