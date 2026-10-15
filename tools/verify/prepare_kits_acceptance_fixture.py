#!/usr/bin/env python3
"""Owned KITS fixtures for Harmony integration; no private author backup needed.

The v3 files are synthetic examples of the documented Octakit import format,
not files produced by Octakit. The real firmware import gate validates them.
Source project is read only; output must be new and separate.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import prepare_mattias_fixture as fixtures


def checksum(block):
    block[-4:] = struct.pack('>I', zlib.crc32(block[:-4]))
    return block


def octakit_files(project):
    bank = (project / 'bank01.work').read_bytes()
    body = fixtures.otp.PART_BASE + 9
    part = bank[body:body + 6322]
    assert len(part) == 6322
    for twin in range(2):
        data = bytearray(0x600 + 256 * 0x1a00)
        for overlay in range(2):
            manifest = bytearray(512)
            manifest[:8] = b'OTK3LINK' if overlay else b'OTK3ROOT'
            struct.pack_into('>I', manifest, 20, 1 + twin * 2 + overlay)
            for pattern in range(256):
                manifest[0x20 + pattern] = (2, 6, 127, 254)[(pattern + twin + overlay) % 4]
                # Keep every pattern assigned: native KITS adopts unassigned
                # patterns during load, whereas this gate compares the imported
                # manifest byte-for-byte after that load has completed.
                manifest[0x120 + pattern // 8] |= 1 << (pattern % 8)
            data[0x200 + overlay * 512:0x400 + overlay * 512] = checksum(manifest)
        for kit in (2, 6, 127, 254):
            record = bytearray(0x1a00)
            record[:8] = b'OTK3KITS'
            record[9] = 1
            struct.pack_into('>I', record, 20, 1 + twin)
            struct.pack_into('>H', record, 24, kit)
            record[0x20:0x27] = f'T{twin}K{kit:03d}'.encode().ljust(7, b'\0')
            record[0x28:0x28 + len(part)] = part
            record[0x28 + 0x12] = 80 + twin * 5 + kit % 4
            checksum(record)
            if twin and kit == 127:
                record[-1] ^= 1  # invalid newer copy must fall back to twin A
            at = 0x600 + kit * 0x1a00
            data[at:at + len(record)] = record
        (project / f'kits3{"ab"[twin]}.work').write_bytes(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    source, out = args.project.resolve(), args.out.resolve()
    if out.exists() or source == out or source in out.parents or out in source.parents:
        raise ValueError('use a new, separate output directory')
    before = fixtures.hashes(source)
    out.mkdir(parents=True)
    subprocess.run([sys.executable, str(Path(__file__).with_name('prepare_degree_kits_fixture.py')),
                    '--project', str(source), '--out', str(out / 'native')], check=True)
    project = out / 'native/project'
    # Upstream's new-project/cold-load assertion expects a nonempty log.
    # An intentionally absent sample supplies a normal FILE NOT FOUND entry;
    # this suite does not stage audio. No error assertion is removed.
    sample = ('[SAMPLE]\r\nTYPE=FLEX\r\nSLOT=001\r\n'
              'PATH=../AUDIO/harmony-fixture-missing.wav\r\nBPMx24=2880\r\n'
              'TSMODE=0\r\nLOOPMODE=1\r\nGAIN=72\r\n'
              'TRIGQUANTIZATION=-1\r\n[/SAMPLE]\r\n').encode()
    for path in project.glob('project.*'):
        path.write_bytes(path.read_bytes() + sample)
    strand, imported = out / 'rejected-bank', out / 'octakit-v3-synthetic'
    shutil.copytree(project, strand)
    bank = bytearray((strand / 'bank01.work').read_bytes())
    bank[-1] ^= 1
    (strand / 'bank01.work').write_bytes(bank)
    shutil.copytree(project, imported)
    for name in ('kits.work', 'kits.strd'):
        (imported / name).unlink(missing_ok=True)
    octakit_files(imported)
    assert fixtures.hashes(source) == before, 'source project changed'
    receipt = dict(source=str(source), source_hashes=before, source_unchanged=True,
                   octakit_provenance='synthetic format fixture, not author-produced files',
                   fixtures={str(p.relative_to(out)): fixtures.hashes(p)
                             for p in (project, strand, imported)})
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: str(p) for k, p in (
        ('project', project), ('strand_project', strand), ('octakit_project', imported))}))


if __name__ == '__main__':
    main()
