#ifndef HARMONY_TRACK_RETENTION_H
#define HARMONY_TRACK_RETENTION_H
#include "packed.h"

/* Each token occupies fields 30/31 of its OWN MIDI step in CS1. The
 * upper six bits carry only metadata for that same pattern/track.
 * Native DRAM, clipboards and HDP3 files retain their existing formats. */
void hd_track_invalidate_c(void);
int hd_track_write_c(const uint8_t *payload, unsigned bank, uint32_t ticket, unsigned status);
void hd_track_commit_c(void);
int hd_track_read_c(uint8_t *payload, unsigned bank, unsigned *status);
#endif
