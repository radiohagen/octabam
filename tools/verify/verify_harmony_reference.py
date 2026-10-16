#!/usr/bin/env python3
"""Compare compiled Harmony/Part State units with the independent author build."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import toolpath
from remix import registry

def main():
    modules={m.key:m for m in registry.selected(registry.remix(sys.argv[1]))}
    if {'MIDI FOLLOW','MIDI SCALES','MIDI SCENES','HARMONY PLOCKS'} & set(modules):
        raise SystemExit('This pin qualifies Harmony/Part State retention variants without optional bridges')
    source=ROOT/'modules/midi-loopback/upstream'
    subprocess.run([sys.executable,str(source/'tools/verify_harmony_reference.py')],check=True)
    records=json.loads((source/'harmony-reference.json').read_text())
    variant=modules['MIDI HARMONY'].build_values.get('RETENTION','LEGACY')
    labels=['midipartsetup','midipart','midipartcopy',*[u[0] for u in records['units']]]
    if variant!='LEGACY':labels.insert(3,'midisram')
    if variant=='MIDI TRACK':labels.append('degreetrack')
    layout=json.loads((ROOT/'out/platform/layout.json').read_text())
    positions={item[1]:i for i,item in enumerate(layout['units'])}
    objects=[ROOT/'out/platform/runtime'/f'{positions[label]:02d}_{label}.o' for label in labels]
    with tempfile.TemporaryDirectory(prefix='harmony-adapter-reference-') as tmp:
        out=Path(tmp)
        subprocess.run(['m68k-elf-ld','-Ttext='+records['runtime_address'],'--defsym=mp_copy_target=0x400d6bb8','--defsym=mp_init_target=0x400d6bbc','-o',str(out/'runtime.elf'),*map(str,objects)],check=True)
        subprocess.run(['m68k-elf-objcopy','-O','binary',str(out/'runtime.elf'),str(out/'runtime.bin')],check=True)
        data=(out/'runtime.bin').read_bytes()
    got={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    assert got==records['artifacts'][variant],(variant,got,records['artifacts'][variant])
    print('[ok] installed Harmony '+variant+' objects match independent author reference')
if __name__=='__main__':main()
