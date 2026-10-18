from pathlib import Path
import concurrent.futures,hashlib,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));import toolpath,emu_card
import argparse
ap=argparse.ArgumentParser(description='Native A03 EXT to A02 INT regression, with/without retained audio T1. Uses a disposable LB-CHECK/LB-FRESH v23 fixture; never writes the source.')
ap.add_argument('--image',type=Path,required=True)
ap.add_argument('--runtime',type=Path,required=True)
ap.add_argument('--project',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args(); OUT=a.out.resolve(); OUT.mkdir(parents=True,exist_ok=False)
SOURCE=a.project.resolve(); image=a.image.resolve()
sym={f[2]:int(f[0],16) for line in subprocess.check_output(['m68k-elf-nm',str(a.runtime)],text=True).splitlines() if len(f:=line.split())==3 and f[1]!='U'}
# Explicit fixture contract: A02 uses Part 1 INT, A03 uses Part 2 EXT,
# MIDI T1 on channel 2 in each Part, 120 BPM. Refuse unrelated projects.
raw=(SOURCE/'bank01.work').read_bytes()
assert raw[21]==23
for pattern,part in [(1,0),(2,1)]:
 assert raw[0x16+(pattern+1)*0x8eec-5]==part
 base=0x8eed6+part*0x18bb+9+0x4e2
 assert raw[base]==2 and raw[base+12]==(4 if part==0 else 0)
assert b'TEMPOx24=2880' in (SOURCE/'project.work').read_bytes()
audio=[f'{p}:{p.relative_to(SOURCE.parent)}' for p in (SOURCE.parent/'AUDIO').rglob('*.wav')]

def decode_notes(path):
 status=None; data=[]; notes=[]
 for line in path.read_text().splitlines():
  fields=line.split(); frame=int(fields[0])
  for token in fields[1:]:
   value=int(token,16)
   if value>=0xf8: continue
   if value&0x80:
    status=value if value<0xf0 else None; data=[]; continue
   if status is None: continue
   data.append(value)
   size=1 if status&0xf0 in (0xc0,0xd0) else 2
   if len(data)==size:
    if status==0x91 and data[1]>0: notes.append(frame*16/44.1)
    data=[]
 return notes

def key(t,k):return f'{t} key {k:#x} down\n{t+80} key {k:#x} up\n'
def run(case):
 trig,stopped=case
 w=OUT/(('with-trig' if trig else 'without-trig')+'-'+('stopped' if stopped else 'playing'));w.mkdir()
 project=w/'project';shutil.copytree(SOURCE,project)
 for path in [project/'bank01.work',project/'bank01.strd']:
  if not path.exists():continue
  raw=bytearray(path.read_bytes())
  offset=0x2e+2*0x8eec # native pattern A03, audio T1 step-1 trig bit
  raw[offset]=(raw[offset]&~1)|int(trig)
  raw[-2:]=(sum(raw[16:-2])%65536).to_bytes(2,'big');path.write_bytes(raw)
 card,_=emu_card.stage_project(project,'LOOPBACK-TEST','LB-CHECK',tree=w/'tree',audio=audio)
 (w/'card.img').write_bytes(card)
 script='100 key 0x2e down\n200 key 0x02 down\n280 key 0x02 up\n400 key 0x2e up\n'
 script+=key(700,0x28)
 if stopped:script+=key(3300,0x27)
 script+='3800 key 0x2e down\n3900 key 0x01 down\n3980 key 0x01 up\n4100 key 0x2e up\n'
 if stopped:script+=key(4600,0x28)
 script+='9000 quit\n';(w/'panel.txt').write_text(script)
 watches=';'.join([f'{sym[s]:#x},{n}' for s,n in [('lb_routes',8),('lb_contexts',32)]]+['0x80001828,18','0x80000002,3','0x100b14cf,1','0x46c7a934,1','0x8000666e,16'])
 dumps=';'.join([f'{sym[s]:#x},{n}={w}/{s}.bin' for s,n in [('lb_routes',8),('lb_contexts',32),('lb_accepted',4),('lb_delivered',4)]]+[
 f'0x46c7a934,1={w}/midi_part.bin',f'0x80001828,18={w}/engine.bin',f'0x80000000,8={w}/current.bin',f'0x100b14cc,4={w}/ui.bin',f'0x400e21e0,635712={w}/bank.bin'])
 cmd=[str(ROOT/'out/emu/ot_emu'),'--image',str(image),'--card',str(w/'card.img'),'--set','LOOPBACK-TEST','--project','LB-CHECK','--mkii','--load-ms','90000','--live-script',str(w/'panel.txt'),'--midi-out',str(w/'wire.midi'),'--watch-mem',watches,'--mem-dump',dumps]
 (w/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with (w/'run.log').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 assert r.returncode==0 and 'ended on quit' in (w/'run.log').read_text(),w
 row={s:(w/f'{s}.bin').read_bytes().hex() for s in ['lb_routes','lb_contexts','lb_accepted','lb_delivered','engine','current','ui','midi_part']}
 notes=decode_notes(w/'wire.midi.frames')
 row['first_external_note_ms']=min(notes,default=None)
 row['early_external_noteons']=sum(700<=t<3300 for t in notes)
 row['late_external_noteons']=sum(t>=4600 for t in notes)
 (w/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(w.name,json.dumps(row),flush=True)
 assert row['first_external_note_ms'] is not None and 700<=row['first_external_note_ms']<1000, row
 assert row['early_external_noteons']>0 and row['late_external_noteons']==0,row
 assert row['lb_routes'].startswith('01') and row['lb_contexts'].startswith('00000000'),row
 assert row['midi_part']=='00' and int(row['lb_delivered'],16)>0,row
 return w.name,row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(run,[(trig,stopped) for trig in (False,True) for stopped in (False,True)]))
(OUT/'result.json').write_text(json.dumps(dict(image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),results=results,hardware_tested=False),indent=2)+'\n')
