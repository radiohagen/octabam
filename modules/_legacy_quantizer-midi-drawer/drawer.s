/* Stock MIDI path: octave - 1, then the formatter's value argument.
 * SCALE QUANTIZER replaces 0x400449b8..0x400449bf, including the push at
 * 0x400449be that stock's MIDI branch targets. Bypass that branch without
 * touching the quantizer's audio/synth octave path or its pinned source.
 */
    .text
    .global qz_midi_octave
qz_midi_octave:
    move.l 0x400beba2,%d0
    subq.l #1,%d0
    move.l %d0,-(%sp)
    jmp 0x400449c0
