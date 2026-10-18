/* Register history is receiver-local, before Harmony ACC and TRAN. Neither
 * a query nor a generated/arp voice advances it: only a successful note-on.
 * One proposal is cached per source pitch class and ordinary receiver event.
 * Thus repeated queries after a commit cannot pull the same event again. */
#include "gravity.h"
#include <stdint.h>
typedef struct {
    int context, epoch;
    unsigned configuration;
    int8_t previous, pending, pitch_class;
    uint8_t initialized;
} BfGravity;
static BfGravity bf_history[8];

void bf_reset_c(void) {
    for (unsigned t=0;t<8;++t) bf_history[t].initialized=0;
}
void bf_forget_c(unsigned track) {
    if (track<8) bf_history[track].initialized=0;
}
void bf_sync_c(unsigned track) {
    if (track>=8) return;
    BfGravity *s=&bf_history[track];
    /* The common FIXED/SOURCE path needs no history or route scan. */
    if (bf_mode_c(track)!=1) {
        if (s->initialized) s->initialized=0;
        return;
    }
    int context=bf_context_c(track), epoch=bf_epoch_c((unsigned)context);
    unsigned configuration=(unsigned)bf_home_c(track)
        | (1u<<4)
        | ((unsigned)bf_source_c(track)<<6)
        | ((unsigned)bf_resolve_c(track)<<10);
    if (!s->initialized || s->context!=context || s->epoch!=epoch
            || s->configuration!=configuration) {
        s->context=context; s->epoch=epoch; s->configuration=configuration;
        s->previous=-1; s->pending=-1; s->pitch_class=-1; s->initialized=1;
    }
}
void bf_begin_c(unsigned track) {
    if (track>=8) return;
    bf_sync_c(track);
    bf_history[track].pending=-1;
    bf_history[track].pitch_class=-1;
}
int bf_gravity_c(int pitch_class, unsigned track) {
    if (track>=8 || pitch_class<0 || pitch_class>=12) return 256;
    bf_sync_c(track);
    BfGravity *s=&bf_history[track];
    if (!s->initialized) return 256;
    if (s->pitch_class==pitch_class && s->pending>=0) return s->pending;
    int lo=12*bf_home_c(track), hi=lo+11;
    int best=-1, best_score=0x7fffffff, best_outside=0x7fffffff;
    for (int note=pitch_class;note<128;note+=12) {
        int outside=note<lo ? lo-note : note>hi ? note-hi : 0;
        int movement=s->previous<0 ? 0 : note-s->previous;
        int score=movement*movement+outside*outside;
        if (score<best_score || (score==best_score && outside<best_outside)) {
            best=note; best_score=score; best_outside=outside;
        }
    }
    /* Ascending enumeration breaks a remaining tie toward the lower pitch.
     * At OCT10, absent pitch classes start in the nearest valid octave. */
    s->pending=(int8_t)best; s->pitch_class=(int8_t)pitch_class;
    return best;
}
void bf_sent_c(unsigned track) {
    if (track>=8) return;
    bf_sync_c(track);
    if (bf_history[track].initialized && bf_history[track].pending>=0)
        bf_history[track].previous=bf_history[track].pending;
}
