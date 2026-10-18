# Quantizer MIDI Drawer

Historical compatibility helper. Current upstream includes the shared-stack
fix from #741; leave this helper out of current-upstream selections.

Compatibility support for the native MIDI chromatic octave display when
SCALE QUANTIZER is selected. It preserves the MIDI formatter's arguments
across the shared audio/MIDI drawing path.

Adds no controls or storage. The quantizer's audio behavior stays the same.

[Developer notes and verification](DEVELOPMENT.md).
