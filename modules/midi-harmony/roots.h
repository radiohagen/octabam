#ifndef HARMONY_DEGREES_ROOTS_H
#define HARMONY_DEGREES_ROOTS_H
#include <stdint.h>

enum { HD_ROOT_STEPS = 64, HD_ROOT_NONE = 255, HD_ROOT_CODES = 84,
       HD_ROOT_UNKNOWN = 0, HD_ROOT_STOCK = 1, HD_ROOT_HARM = 2 };

/* One pattern/track's durable representation. Defaults are native Part data.
 * NOTE snapshots detect native edits; they are never another playable lane.
 * context is bank*4+working Part, or NONE after that Part is overwritten.
 * scale stores mode*12+tonic, retaining the outgoing scale after detachment.
 * HARM publications canonicalize NOTE to hd_mirror_c(degree); storage rebuilds
 * that exact snapshot. The byte layout here is runtime-only. */
typedef struct {
    uint8_t degree[HD_ROOT_STEPS];
    uint8_t note[HD_ROOT_STEPS];
    uint8_t state, scale, context;
} HdRoots;
_Static_assert(sizeof(HdRoots) == 131, "pattern root representation ABI");

void hd_roots_reset_c(HdRoots *roots);
/* Stable native NOTE mirror for an explicit DEG, independent of KEY. */
unsigned hd_mirror_c(unsigned degree);
int hd_roots_valid_c(const HdRoots *roots);
/* Apply an explicit incoming context. Return native roots changed, or -1
 * without mutation for invalid input. Caller publishes returned notes and
 * state together; this helper does not access native memory or own a lock. */
int hd_roots_sync_c(HdRoots *roots, const uint8_t *notes, uint8_t *result,
                    unsigned harm, unsigned scale, unsigned context);
/* Called before a native Part is replaced, with its last effective scale.
 * Detach only matching provenance; never convert roots or adopt new defaults. */
int hd_roots_detach_c(HdRoots *roots, unsigned context, unsigned scale);

#endif
