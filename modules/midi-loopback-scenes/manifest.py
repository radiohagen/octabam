"""Route MIDI Scenes' replacement CC producers through MIDI Loopback."""
import hashlib
from pathlib import Path
from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Override, Proof

# This bridge reads the mix context beside scn_state and qualifies the two
# producer regions. Refuse source drift until those boundaries are re-audited.
SCENES = Path(__file__).resolve().parents[1] / 'midi-scenes/scenes.s'
def boundaries(_modules):
    # c3f37e5 plus the queued handoff guard: only qcommit/step/follow and
    # appended volatile words change. Producer spans scn_ccnote..scn_clear
    # and public scn_state+288/+292 retain their contracts.
    assert hashlib.sha256(SCENES.read_bytes()).hexdigest() == 'a3da3a495f33265912f3b35258d499cc3072b54af1c167a7a42a8da7caff93ef', 'MIDI Scenes bridge needs a source-boundary audit'
    return ''

MODULE = Module(
    name='midi-loopback-scenes', key='MIDI LOOPBACK SCENES', kind=Kind.CF_PATCH,
    category=Category.MIDI_USB, author='radiohagen',
    author_url='https://github.com/radiohagen/octatrack-modules',
    doc='Compose MIDI Loopback destinations with MIDI Scenes CC output and USB MIDI.',
    proof=Proof.CHECK, proof_note='',
    requires=('MIDI LOOPBACK', 'MIDI SCENES', 'USB'),
    linked=(Linked('loopbackscenes', 'modules/midi-loopback-scenes/bridge.s', dram=True, include=boundaries),),
    detours=(Detour(0x40010bc8, bytes.fromhex('4fefffec48d7043c'),
                   'loopbackscenes', 'lb_scenes_send',
                   'Scenes CC loop routes before the unchanged USB/DIN sender', pad_to=8),),
    overrides=(Override(0x40010bc8, 'USB'),),
    gates=(Gate('tools/verify/verify_midi_loopback_scenes.py', venv=True, stage='image'),),
)
