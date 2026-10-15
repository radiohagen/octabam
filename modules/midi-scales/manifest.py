"""Extend the stock MIDI KEY selector, retaining its Part storage and UI."""
from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Poke, Proof, SymbolRef

def options(modules):
    return ('.set HAVE_FOLLOW,1\n' if 'MIDI FOLLOW' in modules else '') + ('.set HAVE_HARMONY,1\n' if 'MIDI HARMONY' in modules else '')

MODULE = Module(
    name='midi-scales',key='MIDI SCALES',kind=Kind.CF_PATCH,
    category=Category.MIDI_USB,author='Mattias Wolff',author_url='https://github.com/mattiaswolff/octabam',
    proof=Proof.PORT,proof_note='verify_midi_scales: all 84 keys over 128 notes under the port; hardware untested',
    doc='Stock MIDI ARP SETUP KEY: OFF plus all 12 keys in seven diatonic modes, stored in the Part.',
    linked=(Linked('midiscales','modules/midi-scales/scales.s',dram=True,include=options),),
    pokes=(Poke(0x400d4096,bytes.fromhex('00000019'),bytes.fromhex('00000055'),'85 KEY values'),),
    symbol_refs=(SymbolRef(0x400d40c6,0x4003b790,'midiscales','ms_format','stock two-line KEY formatter'),),
    detours=(
        Detour(0x4007a3e2,bytes.fromhex('7205b280660000e4'),'midiscales','ms_encoder','KEY combinations and inherited read-only source',pad_to=8),
        Detour(0x4009fb58,bytes.fromhex('4aaeffc06f22'),'midiscales','ms_output','extra scales at stock output quantization point'),
    ),
    gates=(Gate('tools/verify/verify_midi_scales.py',stage='image',venv=True),),
)
