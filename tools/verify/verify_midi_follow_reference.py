#!/usr/bin/env python3
"""Compare installed Follow/Part State objects with the pinned author build."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import toolpath  # noqa: F401,E402
from remix import registry


def main():
    modules=registry.remix(sys.argv[1]).modules
    if 'MIDI FOLLOW' not in modules:raise SystemExit('Follow reference requires MIDI FOLLOW')
    if {'MIDI HARMONY','MIDI SCALES'} & set(modules):
        raise SystemExit('This author pin qualifies standalone Follow and Follow/Loopback only')
    source=ROOT/'modules/midi-loopback/upstream'
    subprocess.run([sys.executable,str(source/'tools/verify_follow_reference.py')],check=True)
    records=json.loads((source/'follow-reference.json').read_text())
    combo='MIDI LOOPBACK' in modules
    labels=['midipartsetup','midipart','midipartcopy','bassfollow','followresponse','followregister','followsettings','followpage']
    if combo:labels += ['loopback','loopbackproducers','loopbacksettings','loopbackpage']
    layout=json.loads((ROOT/'out/platform/layout.json').read_text())
    positions={item[1]:i for i,item in enumerate(layout['units'])}
    objects=[ROOT/'out/platform/runtime'/f'{positions[label]:02d}_{label}.o' for label in labels]
    with tempfile.TemporaryDirectory(prefix='follow-adapter-reference-') as tmp:
        out=Path(tmp)
        subprocess.run(['m68k-elf-ld','-Ttext='+records['runtime_address'],'--defsym=mp_copy_target=0x400d6bb8','--defsym=mp_init_target=0x400d6bbc','-o',str(out/'runtime.elf'),*map(str,objects)],check=True)
        subprocess.run(['m68k-elf-objcopy','-O','binary',str(out/'runtime.elf'),str(out/'runtime.bin')],check=True)
        data=(out/'runtime.bin').read_bytes()
    got={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    key='follow-loopback' if combo else 'follow'
    assert got==records['artifacts'][key],(key,got,records['artifacts'][key])
    print('[ok] installed '+key+' objects match the independently built author reference')

if __name__=='__main__':main()
