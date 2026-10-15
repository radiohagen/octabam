#!/usr/bin/env python3
"""Create a separate, deterministic project for the combined KITS gate.

The gate expects bank 3, rotating Part assignments, pattern 14 as the first
empty pattern, enabled external transport/program reception and LEVEL headroom.
In-scale roots make native pattern-byte copy assertions meaningful with DEG.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import verify_midi_harmony_port as p


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path,help='new fixture directory; must not exist')
    args=ap.parse_args()
    source=args.project.resolve();dest=args.out.resolve()
    assert (source/'project.work').is_file(), 'source project is missing'
    assert not dest.exists() and not dest.is_relative_to(source), 'use a new separate output directory'
    p.OUT=dest.parent
    work=p.fixture(source,dest.name,{0:2,1:2})
    values=dict(BANK=2,MIDI_CLOCK_RECEIVE=1,MIDI_TRANSPORT_RECEIVE=1,
                MIDI_PROGRAM_CHANGE_RECEIVE=1,MIDI_PROGRAM_CHANGE_RECEIVE_CH=0)
    for path in (work/'project').glob('project.*'):
        raw=path.read_bytes()
        for key,value in values.items():
            raw,count=re.subn(rb'(?m)^'+key.encode()+rb'=[^\r\n]*',key.encode()+b'='+str(value).encode(),raw)
            assert count==1,(path.name,key,count)
        path.write_bytes(raw)
    for path in (work/'project').glob('bank*.work'):
        bank=int(path.stem[4:])
        def seed(data):
            starts=[m.start() for m in re.finditer(b'PTRN',data)]+[p.otp.PART_BASE]
            assert len(starts)==17
            for pattern in range(16):data[starts[pattern+1]-5]=pattern%4
            for part in range(8):
                base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                for track in range(8):
                    data[base+0x12+2*track]=100
                    data[base+0x4e2+track*36+17]=1
                    data[base+0x4e2+track*36+19]=35
            if bank==3:
                for pattern in range(1,13):data[p.otp.trac_off(pattern,0)+7]|=1
        p.otp._bank_write(work/'project',bank,seed,guard=False)
    receipt={'source':str(source),'source_read_only':True,'bank':3,
             'degree_default':'1:3','key':'C major','levels':100,
             'bank3_first_empty_pattern':14,'project_settings':values,
             'files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest()
                      for x in sorted((work/'project').iterdir()) if x.is_file()}}
    (work/'fixture.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(work/'project')


if __name__=='__main__':main()
