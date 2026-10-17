#ifndef HARMONY_DEGREES_PACKED_H
#define HARMONY_DEGREES_PACKED_H
#include "core.h"

/* Root/quality section: one metadata byte and 64 10-bit tokens per lane.
 * Context is transient and always detached on import. Playback keeps the
 * unpacked representation: storage packing never changes the musical lanes. */
enum { HD_PACKED_LANE = 81, HD_PAYLOAD_BYTES = HD_LANES * HD_PACKED_LANE };
_Static_assert(HD_PAYLOAD_BYTES == 10368, "root payload ABI");

int hd_pack_c(const HdBank *bank, const uint8_t *qualities, volatile uint8_t *payload);
int hd_packed_valid_c(const volatile uint8_t *payload);
/* Validate the entire payload before publishing either destination. */
int hd_unpack_c(HdBank *bank, uint8_t *qualities, const volatile uint8_t *payload);
#endif
