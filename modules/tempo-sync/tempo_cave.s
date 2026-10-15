| BusDelay MIDI-note publish -- a DRAM unit entered by a jsr at 0x40004d40
|
| Hooked from 0x40004d40 in the per-frame voice-record writer (0x40004bd2),
| the routine that publishes the FX ids into the 32-halfword record the DSP
| receives (one halfword -> one 24-bit word, <<8). The three displaced
| instructions are replayed first; then, for a track whose FX2 id is 6
| (DELAY SERVER), the held MIDI note goes into the LOW byte of halfword 13
| (record +0x1b, DSP word r6+$1 bits 8-15 of the FX2 instance): BusDelay's
| TIME word, whose knob decode masks to bits 16-23. The copier, the slew
| and the scene stage write every page-1 halfword as value<<8 with a zero
| low byte, and all three run before this writer, so the store lands last
| in the frame.
|
| The tempo is not published here: stock writes tempo24 (0x8000181c) into
| halfword 31 of every track's record (0x40004d6a, `move.w %a0,0x3e(%a2)`)
| and BusDelay reads it at r6+$13 and derives samples-per-MIDI-clock itself.
|
| Until 15 Sep 2026 this cave stored tempo24, ticks, fader+1 and the note
| into halfwords 18-21 (+0x24..+0x2a). Halfwords 18-20 are the FX1
| instance's page 2 (r6_FX1+$c..$e) and 21 is the AMP page 2's first word,
| so every FX1 effect on a delay or reverb host ran page 2 on the tempo
| bytes (FAILURE_MODES "An FX1 station's page 2 does not reach the DSP on
| a bus host"; measured under the port with a write watch on the record).
|
| a0 = 0x80000110 + track (id array base), a2 = this track's record,
| d4 = the track index (0..7) -- from the writer's disassembly at
| 0x40004d38 (`moveal %d4,%a0 ; addal #0x80000110,%a0`). a0 is reloaded
| from d5 right after the hook (0x40004d4a). Clobbers nothing: d0/a0 saved.
|     note byte: 0x400d64c2[track], 0xff when released -> 0.

        .text
        .global tempo_note_publish, tempo_note_replay
tempo_note_publish:
        move.b  0xdbc(%a0),%d2          | displaced: FX2 id
        ext.w   %d2                     | displaced
        move.w  %d2,0x38(%a2)           | displaced: -> record +0x38 (x:$208+$1c)
        cmpi.w  #6,%d2                  | DELAY SERVER only
        bne.s   skip
        move.l  %d0,-(%sp)
        move.l  %a0,-(%sp)
        lea     0x400d64c2,%a0          | held-note bytes, one per track
        move.b  (%a0,%d4.l),%d0
        move.l  (%sp)+,%a0
        and.l   #0xff,%d0
        cmpi.l  #0xff,%d0               | 0xff = released
        bne.s   nkeep
        clr.l   %d0
nkeep:  move.b  %d0,0x1b(%a2)           | halfword 13 low byte = note or 0
        move.l  (%sp)+,%d0
skip:   rts

| CAVE REPLAY (a diagnostic): the displaced instructions and nothing else,
| so the hook can be told apart from the store. The three instructions hold
| no pc-relative operand.
tempo_note_replay:
        move.b  0xdbc(%a0),%d2
        ext.w   %d2
        move.w  %d2,0x38(%a2)
        rts
