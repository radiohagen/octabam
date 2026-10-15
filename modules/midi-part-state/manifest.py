"""Shared native Part access and coherent publication for MIDI modules."""
from remix.schema import Category, Claims, Detour, Gate, Kind, Linked, Module, Poke, Proof

MODULE = Module(
    name='midi-part-state', key='MIDI PART STATE', kind=Kind.CF_PATCH,
    category=Category.PARTS, author='Mattias Wolff',
    author_url='https://github.com/mattiaswolff/octabam', proof=Proof.PORT,
    proof_note='verify_midi_part_copy and verify_midi_part_settings: linked native boundaries; hardware untested',
    doc='Shared native Part settings and coherent copy/clear publication; no KITS dependency.',
    linked=(Linked('midipartsetup', 'modules/midi-part-state/setup.s', dram=True,
                   include=lambda modules: ('.set HAVE_FOLLOW,1\n' if 'MIDI FOLLOW' in modules else '') +
                   ('.set HAVE_HARMONY,1\n' if 'MIDI HARMONY' in modules else '')),
            Linked('midipartentry', 'modules/midi-part-state/entry.s'),
            Linked('midipart', 'modules/midi-part-state/part.s', dram=True,
                   include=lambda modules: '.set MP_DEFINE,1\n'),
            Linked('midipartcopy', 'modules/midi-part-state/part-copy.s', dram=True,
                   defsyms=(('mp_copy_target',0),('mp_init_target',0)),
                   include=lambda modules: '.set MP_DEFINE,1\n' + ('.set HAVE_HARMONY,1\n' if 'MIDI HARMONY' in modules else '') + ('.set HAVE_MIDI_SRAM,1\n' if 'MIDI SRAM' in modules else ''))),
    detours=(Detour(0x4004af20, bytes.fromhex('4fefffd448d77cfc'),
                    'midipartsetup', 'mp_note_confirm', 'preserve live module settings on NOTE SETUP YES', pad_to=8),
             Detour(0x40000512, bytes.fromhex('4eb94000f938'),
                    'midipartcopy', 'mp_activate', 'enable Part boundaries after native platform load', kind='jsr'),
             Detour(0x40020898, bytes.fromhex('2f02226f0008'),
                    'midipartentry', 'mp_copy_entry', 'coherent native MIDI Part copies'),
             Detour(0x40005638, bytes.fromhex('4fefffa848d77cfc'),
                    'midipartentry', 'mp_init_entry', 'coherent native MIDI Part initialization', pad_to=8)),
    pokes=(Poke(0x400d4082, bytes.fromhex('00000001'), bytes.fromhex('00000010'), 'Follow/Loopback Part flags range'),),
    claims=Claims(part_window=tuple((0x4e2+36*t+12, 1, 'shared MIDI Part flags') for t in range(8))),
    gates=(Gate('tools/verify/verify_midi_part.py', stage='image', venv=True),
           Gate('tools/verify/verify_midi_part_copy.py', stage='image', venv=True),
           Gate('tools/verify/verify_midi_part_settings.py', stage='image', venv=True)),
)
