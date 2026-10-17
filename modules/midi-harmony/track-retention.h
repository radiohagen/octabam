#ifndef HARMONY_TRACK_RETENTION_H
#define HARMONY_TRACK_RETENTION_H
#include "packed.h"
#include "accumulator.h"
enum { HD_TRACK_PAYLOAD_BYTES = HD_PAYLOAD_BYTES + HA_BANK_BYTES };

/* Fields 30/31 of each OWN MIDI step in CS1: ten token bits, four ACC
 * bits, two metadata bits. Native DRAM/clipboard/bank formats are unchanged;
 * Harmony's own copy hooks and HDP4 companion carry musical metadata. */
void hd_track_invalidate_c(void);
int hd_track_write_c(const uint8_t *payload, unsigned bank, uint32_t ticket, unsigned status);
void hd_track_commit_c(void);
int hd_track_read_c(uint8_t *payload, unsigned bank, unsigned *status);
#endif
