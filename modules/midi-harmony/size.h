#ifndef HARMONY_SIZE_H
#define HARMONY_SIZE_H
#include <stdint.h>
/* config: VOIC[2:0], SPRD[4:3], ROOT[6:5], SIZE[8:7].
 * history is the existing four pitches + big-endian root/context token.
 * source_scale: scale[9:0], effective source[12:10]. */
void mh_size_voice_c(uint8_t pool[4], uint8_t history[8], unsigned config,
                     unsigned quality, unsigned source_scale);
#endif
