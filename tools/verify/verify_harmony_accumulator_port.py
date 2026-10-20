#!/usr/bin/env python3
"""Accumulator through real UART panel events, sequencer and disposable CF.

No configuration is injected into the accumulator table: defaults and locks
are entered with encoders/trigs. Memory dumps observe the resulting state.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import verify_midi_harmony_port as p
import verify_chord_play_port as cp
from verify_harmony_degree_integration import symbols

PANEL='100 key 0x31 down\n200 key 0x31 up\n300 key 0x35 down\n350 key 0x35 up\n500 key 0x22 down\n600 key 0x22 up\n'
GRID='800 key 0x29 down\n900 key 0x29 up\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True,type=Path)
    ap.add_argument('--output',type=Path,default=p.ROOT/'out/harmony-accumulator-port')
    ap.add_argument('--candidate',type=Path,help='frozen directory containing candidate.bin and candidate-symbols.json')
    ap.add_argument('--case',choices=('ui','play','reset','settings','controls','resume','save','chord','arp','follow','gravity'),action='append')
    args=ap.parse_args()
    if not (args.project/'project.work').is_file() or not any(args.project.glob('bank*.work')):
        ap.error('--project must contain project.work and at least one working bank')
    p.OUT=args.output
    if args.candidate:
        p.CANDIDATE_IMAGE=args.candidate/'candidate.bin'
        s=json.loads((args.candidate/'candidate-symbols.json').read_text())
        p.harmony.symbols=lambda:s
    else:
        p.freeze_candidate(p.OUT);s=symbols()
    results={}
    work=p.fixture(args.project,'panel-note',{0:1},first_note=48)
    # A short, repeating 16-step pattern with the same root on three steps.
    for path in (work/'project').glob('bank*.work'):
        def seed(data):
            for pattern in range(16):
                end=0x16+(pattern+1)*0x8eec
                data[end-9]=16
            for step in (2,4,8):data[0x492e+0x39+step*32]=48
        p.otp._bank_write(work/'project',int(path.stem[4:]),seed,guard=False)
    card,_=p.emu_card.stage_project(work/'project','OCTABAM','BASS',tree=work/'accum-tree')
    (work/'card.img').write_bytes(card)
    edit=PANEL+GRID+'''1200 enc 4 1
1700 key 4 down
2100 enc 4 -1
2500 key 4 up
2900 key 8 down
3300 enc 4 1
3700 key 8 up
'''
    def run(name,script,extra=(),card=None,physical_panel=False):
        path=work/f'{name}.txt';path.write_text(script)
        events=p.run(work,name,['--live-script',path,'--internal-clock','--lcd',work/f'{name}.lcd',
            '--mem-dump',f'{s["ha_lanes"]:#x},4736={work}/{name}-acc.bin;0x10000000,0x100000={work}/{name}-cs1.bin',*extra],card=card,physical_panel=physical_panel)
        p.balanced(events)
        subprocess.run([sys.executable,str(p.ROOT/'tools/emu/lcd_view.py'),str(work/f'{name}.lcd'),
                        '--png',str(work/f'{name}.png')],check=True)
        return [e[2] for e in events if e[:2]==('on',1)]
    cases=set(args.case or ('ui','play','reset','settings','controls','resume','save','chord','arp','follow','gravity'))
    if cases & {'ui','play','resume'}:
        run('edit',edit+'4300 quit\n')
        cfg=(work/'edit-acc.bin').read_bytes()
        assert cfg[36]==9 and cfg[2]>>4==1 and cfg[4]>>4==10,list(cfg[:37])
        assert all(b==0 for i,b in enumerate(cfg[:32]) if i not in (2,4))
        results['panel_defaults_and_locks']='passed'
        print('[ok] real E default +1; held step 5 OFF and step 9 +2; other steps inherit',flush=True)
    if 'play' in cases:
        script=edit+'''4300 key 0x28 down
4400 key 0x28 up
13000 key 0x27 down
13100 key 0x27 up
14200 quit
'''
        notes=run('play',script)
        tones=(0,2,4,5,7,9,11)
        want=[]
        for cycle in range(8):
            first=cycle%8;third=(cycle*2)%8
            want += [48+12*(first//7)+tones[first%7],48,48+12*(third//7)+tones[third%7]]
        assert len(notes)>=9 and notes==want[:len(notes)],(notes,want)
        results['sequence']=notes
        print('[ok] native sequence, independent offsets and explicit OFF:',notes,flush=True)
    if 'resume' in cases:
        run('resume','2500 quit\n',('--no-post','--cs1-in',work/'edit-cs1.bin'),work/'edit-card.img')
        assert (work/'resume-acc.bin').read_bytes()==(work/'edit-acc.bin').read_bytes()
        results['unsaved_retained_restart']='passed'
        print('[ok] unsaved encoder edits survive retained-memory restart',flush=True)
    if 'reset' in cases:
        prefix=PANEL+'''1200 enc 4 1
1800 key 0x28 down
1900 key 0x28 up
6600 key 0x27 down
6700 key 0x27 up
'''
        first=run('before-restart',prefix+'7300 quit\n')
        notes=run('transport-restart',prefix+'''7600 key 0x28 down
7700 key 0x28 up
12000 key 0x27 down
12100 key 0x27 up
13200 quit
''')
        assert len(first)>=6 and notes[:len(first)]==first,(first,notes)
        assert notes[len(first):len(first)+6]==[48,48,48,50,50,50],notes
        results['native_transport_reset']='passed'
        print('[ok] native STOP/PLAY resets independent phases under RESET BOTH',flush=True)
    if cases & {'settings','controls'}:
        setup=PANEL+'''1000 key 0x2d down
1100 key 0x22 down
1200 key 0x22 up
1300 key 0x2d up
1700 key 0x3d down
1800 key 0x3d up
'''
        run('harmony-page',setup+'2600 quit\n')
        run('chord-page-extremes',setup+'''2100 enc 0 3
2500 enc 1 2
2900 enc 2 3
3300 enc 3 3
3900 quit
''')
        part=0xa4ece+0x4e2
        state=(work/'chord-page-extremes-cs1.bin').read_bytes()
        assert state[part+5]==1 and state[part+16]==116 and state[part+18]==24
        run('accum-page',setup+'''2100 key 0x20 down
2200 key 0x20 up
2500 enc 0 -7
3500 enc 1 7
4500 enc 2 1
5000 enc 3 -2
5600 quit
''')
        cfg=(work/'accum-page-acc.bin').read_bytes()
        assert cfg[32:37]==bytes((249,14,1,1,1)),list(cfg[:37])
        # Real encoder edits cover every switch position and longest signed
        # limits. No configuration or LCD pixels are injected.
        for mode,(low,high) in enumerate(((-21,21),(-1,0),(0,7),(-21,21))):
            script=setup+'2100 key 0x20 down\n2200 key 0x20 up\n'
            at=2500
            # Space physical reports so redraws cannot coalesce a long sweep.
            # Deliberately overshoot both limits to verify the three-octave cap.
            for knob,delta in enumerate((low-2 if low==-21 else low,
                                         high-7+2 if high==21 else high-7,mode,mode-3)):
                for _ in range(abs(delta)):
                    script+=f'{at} enc {knob} {4 if delta>0 else -4}\n'
                    at+=100
            run(f'accum-state-{mode}',script+f'{at+600} quit\n',physical_panel=True)
            cfg=(work/f'accum-state-{mode}-acc.bin').read_bytes()
            assert cfg[32:37]==bytes((low&255,high,mode,mode,1)),list(cfg[:37])
        run('chord-page-return',setup+'''2100 key 0x20 down
2200 key 0x20 up
2600 key 0x33 down
2700 key 0x33 up
3300 quit
''')
        from verify_harmony_accumulator_ui import lcd_view
        # Navigation back must clear the taller ACCUM grid and restore CHORD.
        assert lcd_view.screen(lcd_view.read_plane(work/'chord-page-return.lcd'))==lcd_view.screen(
            lcd_view.read_plane(work/'harmony-page.lcd')),'CHORD pixels changed after ACCUM'
        results['setup_navigation']='passed'
        from verify_harmony_accumulator_ui import measure
        results['pixel_layout']=measure(work)
        print('[ok] CHORD A-D reshapes voicing without changing HARM; ACCUM A-D edits track settings',flush=True)
    if 'controls' in cases:
        # Test each visible cell independently, so swapped mappings cannot
        # hide behind a combined final state. E/F are empty in both sections.
        baseline=(work/'harmony-page-cs1.bin').read_bytes()[part:part+36]
        initial=(work/'harmony-page-acc.bin').read_bytes()
        for tab in range(2):
            select='2100 key 0x20 down\n2200 key 0x20 up\n' if tab else ''
            for knob in range(6):
                delta=-1 if tab and knob in (0,3) else 1
                name=f'cell-{tab}-{knob}'
                run(name,setup+select+f'2600 enc {knob} {delta}\n3300 quit\n')
                state=(work/f'{name}-cs1.bin').read_bytes()[part:part+36]
                cfg=(work/f'{name}-acc.bin').read_bytes()
                expected=bytearray(baseline);acc=bytearray(initial)
                if knob<4:
                    if tab:acc[32+knob]=(acc[32+knob]+delta)&255
                    elif knob==3:expected[18]=8
                    else:expected[16]=(2,8,32)[knob]
                assert state==expected,(name,list(state),list(expected))
                assert cfg==acc,(name,list(cfg[:37]),list(acc[:37]))
        results['position_to_encoder_mapping']='A/B/C top, D bottom left; empty E/F inert'
        print('[ok] every displayed cell edits only its positional encoder value; empty E/F are inert',flush=True)
        # The section selector and dotted cells are compared with the native
        # LFO SETUP screen in the same firmware, at the same LCD resolution.
        run('native-lfo',PANEL+'1000 key 0x2d down\n1100 key 0x24 down\n1200 key 0x24 up\n1300 key 0x2d up\n2300 quit\n')
        run('held-settings',setup.replace(PANEL,PANEL+GRID)+'''2100 key 0x20 down
2200 key 0x20 up
2400 key 4 down
2600 enc 0 -1
3000 key 4 up
3600 quit
''')
        cfg=(work/'held-settings-acc.bin').read_bytes()
        assert cfg[32]==255 and cfg[:32]==bytes(32),list(cfg[:37])
        # Push held E removes the explicit lock, retaining the track default.
        run('inherit',edit+'''4100 key 8 down
4400 key 0x3c down
4500 key 0x3c up
4800 key 8 up
5400 quit
''')
        cfg=(work/'inherit-acc.bin').read_bytes()
        assert cfg[4]>>4==0 and cfg[36]==9,list(cfg[:37])
        results['standard_controls']='passed'
        print('[ok] held E push restores inheritance; held trigs do not lock setup settings',flush=True)
    if 'save' in cases:
        run('save',edit+cp.SAVE,('--rtc','1800000000'))
        expected=(work/'save-acc.bin').read_bytes()
        assert expected[36]==9 and expected[2]>>4==1 and expected[4]>>4==10
        files=p.emu_card.extract_image((work/'save-card.img').read_bytes())
        for suffix in ('work','strd'):
            file=files[f'OCTABAM/BASS/hdeg01.{suffix}']
            assert file[:8]==b'HDP4\0\0\0\4' and file[10400:]==expected
        run('reload','2500 quit\n',card=work/'save-card.img')
        assert (work/'reload-acc.bin').read_bytes()==expected
        results['native_project_save_reload']='passed'
        print('[ok] native SAVE PROJECT writes working/stored HDP4; cold load reproduces ACC',flush=True)
    tones=(0,2,4,5,7,9,11)
    def degree_shift(note,amount):
        octave,degree=divmod((note//12)*7+tones.index(note%12)+amount,7)
        return octave*12+tones[degree]
    def quant(note):
        return min((n for n in range(128) if n%12 in tones),key=lambda n:(abs(n-note),n))
    for case in ('chord','arp','follow','gravity'):
        if case not in cases:continue
        work=p.fixture(args.project,case,{0:2 if case!='arp' else 1,1:1},first_note=48,arp=case=='arp')
        for path in (work/'project').glob('bank*.work'):
            def seed(data):
                for pattern in range(16):data[0x16+(pattern+1)*0x8eec-9]=16
                for step,note in zip((2,4,8),((59,60,65) if case=='gravity' else (52,53,55) if case=='follow' else (48,48,48))):
                    data[0x492e+0x39+step*32]=note
                if case in ('follow','gravity'):
                    at=0x492e+0x8b9
                    data[at+9:at+17]=sum(1<<i for i in (2,4,8)).to_bytes(8,'big')
                    for part in range(8):
                        base=p.otp.PART_BASE+part*p.otp.PART_STRIDE+9
                        data[base+0x4e2+36+3]=1 # RFOL T1
                        data[base+0x4e2+36+17]=1 # C major, independent own register
                        if case=='gravity':data[base+0x4e2+36+15]=0x12 # GRAV OCT2
                        data[base+0x3e2+32+2]=1 # release before next source change
            p.otp._bank_write(work/'project',int(path.stem[4:]),seed,guard=False)
        card,_=p.emu_card.stage_project(work/'project','OCTABAM','BASS',tree=work/'accum-tree')
        (work/'card.img').write_bytes(card)
        play='1800 key 0x28 down\n1900 key 0x28 up\n10800 key 0x27 down\n10900 key 0x27 up\n12000 quit\n'
        select='900 key 0x11 down\n1000 key 0x11 up\n' if case in ('follow','gravity') else ''
        if case in ('follow','gravity'):
            run('reference',PANEL+select+play)
            reference=[e[2] for e in json.loads((work/'reference-notes.json').read_text()) if e[:2]==['on',2]]
            assert len(reference)>=9 and reference[:3]*3==reference[:9],reference
            # Native transpose is +1 semitone, entered on ARP MAIN A.
            transpose='1100 key 0x23 down\n1150 key 0x23 up\n1250 enc 0 1\n1400 key 0x22 down\n1450 key 0x22 up\n'
            # Native TRAN consumes raw pitch counts; ACC consumes four-count
            # choice reports. Do not expand native pitch into four semitones.
            run('accum',PANEL+select+transpose+'1550 enc 4 4\n'+play,
                ('--mem-dump',f'0x46c7700c,1={work}/tran.bin'),physical_panel=True)
            assert (work/'tran.bin').read_bytes()==bytes((65,))
            notes=[e[2] for e in json.loads((work/'accum-notes.json').read_text()) if e[:2]==['on',2]]
            want=[quant(degree_shift(n,i//3)+1) for i,n in enumerate(reference)]
            assert notes==want,(notes,want,reference)
        else:
            notes=run('accum',PANEL+'1200 enc 4 1\n'+play)
            if case=='arp':
                changes=[n for i,n in enumerate(notes) if not i or n!=notes[i-1]]
                assert len(notes)>len(changes) and changes[:4]==[48,50,52,53],notes
            else:
                want=[]
                for i in range(20):
                    root=degree_shift(48,(i//3)%8)
                    want += [root,degree_shift(root,2),degree_shift(root,4)]
                assert len(notes)>=27 and notes==want[:len(notes)],(notes,want)
        results[case]=notes
        print('[ok]',case,notes,flush=True)
    receipt=dict(results=results,image_sha256=hashlib.sha256(p.CANDIDATE_IMAGE.read_bytes()).hexdigest(),hardware_tested=False)
    (p.OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
