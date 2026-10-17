/* Physical-key queue provenance. Native message bytes, including the pitch
 * used to release a key, remain unchanged. The companion metadata lasts only
 * until that message is consumed; nothing here belongs in a Part or Kit. */
#include "core.h"
extern uint8_t ch_messages[4096];
typedef struct { uint8_t context, attached; uint16_t scale; } Capture;
static Capture captures[256];

static int index_of(uintptr_t message) {
    uintptr_t offset = message-(uintptr_t)ch_messages;
    return offset < 4096 && !(offset & 15) ? (int)(offset/16) : -1;
}
static unsigned absolute(unsigned degree, unsigned scale) {
    int note = hd_decode_c((int)degree,(int)scale);
    return note >= 0 ? (unsigned)note : degree < 7 ? 0u : 127u;
}
int hd_capture_c(unsigned note, unsigned track) {
    int context = hd_ui_context_c();
    return context < 0 || track >= 8 ? -1 : hd_encode_c((int)note,
            hd_scale_c((unsigned)context/4,(unsigned)context%4,track));
}
int hd_capture_message_c(uintptr_t message, unsigned note, unsigned track) {
    int index = index_of(message), context = hd_ui_context_c();
    if (index < 0 || context < 0 || track >= 8 || note > 127) return HD_NONE;
    unsigned scale = (unsigned)hd_scale_c((unsigned)context/4,(unsigned)context%4,track);
    captures[index] = (Capture){(uint8_t)context,
        (uint8_t)!hd_context_replacing_c((unsigned)context,track),(uint16_t)scale};
    int degree = hd_encode_c((int)note,(int)scale);
    if (hd_busy[track] && hd_busy_context[track] == (unsigned)context && !hd_target[track])
        return (int)(128u | absolute((unsigned)degree,scale));
    return degree;
}
static void convert(unsigned index, unsigned context, unsigned track, unsigned mode) {
    Capture *capture = &captures[index];
    uint8_t *message = ch_messages+index*16;
    unsigned value = message[15];
    if (capture->attached)
        capture->scale = (uint16_t)hd_scale_c(capture->context/4,capture->context%4,track);
    unsigned incoming = (unsigned)hd_scale_c(context/4,context%4,track);
    if (mode && value >= 128) message[15] = (uint8_t)hd_encode_c((int)(value&127),(int)incoming);
    else if (!mode && value < HD_CODES) message[15] = (uint8_t)(128u | absolute(value,capture->scale));
    capture->context = (uint8_t)context;
    capture->scale = (uint16_t)incoming;
    capture->attached = !hd_context_replacing_c(context,track);
}
void hd_record_modes_c(unsigned track, unsigned mode) {
    int context = hd_ui_context_c();
    if (context < 0 || track >= 8 || mode > 2) return;
    for (unsigned i = 0; i < 256; ++i) {
        const uint8_t *message = ch_messages+i*16;
        if (message[14] && message[13] == track && captures[i].context == (unsigned)context)
            convert(i,(unsigned)context,track,mode);
    }
}
void hd_record_part_before_c(unsigned context) {
    for (unsigned i = 0; i < 256; ++i) {
        const uint8_t *message = ch_messages+i*16;
        Capture *capture = &captures[i];
        unsigned track = message[13];
        if (message[14] && capture->attached && hd_context_depends_c(capture->context,track,context)) {
            capture->scale = (uint16_t)hd_scale_c(capture->context/4,capture->context%4,track);
            capture->attached = 0;
        }
    }
}
void hd_record_consume_c(uintptr_t message) {
    int index = index_of(message), context = hd_ui_context_c();
    if (index < 0 || context < 0) return;
    unsigned track = ch_messages[index*16+13];
    if (track >= 8) return;
    convert((unsigned)index,(unsigned)context,track,
            hd_part_type_c((unsigned)context/4,(unsigned)context%4,track));
}
