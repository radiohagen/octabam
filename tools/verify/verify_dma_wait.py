#!/usr/bin/env python3
"""Prove a matched MAIN OS pair changes only BusDelay's 8192 -> 4096 wait.

    python3 tools/verify/verify_dma_wait.py BASE.bin HALF.bin --out receipt.json

Both images must use the same remix and BUILD tag. This is a byte/placement
gate, not a DMA timing or audio test. Packed uploads are decoded from each
image's own boot pointers and checked by image_dsp. Outside the changed
packed upload, only its packed and raw checksum fields may differ. Container
sizes/positions must remain unchanged; a relocated build is refused.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
import ab_records  # noqa: E402
import image_dsp  # noqa: E402


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _packed_entries(data):
    """Physical loader entries, indexed by destination, with bounded blobs."""
    result = {}
    blob = data.find(b"OCTAGKA3")
    while blob >= 0:
        marker = struct.pack(">I", image_dsp.BASE + blob)
        entry = data.find(marker)
        while entry >= 0:
            if entry + 32 <= len(data):
                fields = struct.unpack_from(">8I", data, entry)
                destination, size = fields[4], fields[1]
                if destination in result:
                    raise ValueError("packed upload must have one physical loader entry")
                if size < 12 or blob + size > len(data):
                    raise ValueError("packed upload lies outside image")
                result[destination] = (entry, blob, size)
            entry = data.find(marker, entry + 1)
        blob = data.find(b"OCTAGKA3", blob + 8)
    return result


def _upload(data, tag):
    """Return verified records, their exact source bytes and container bounds."""
    at = image_dsp.BOOT_POINTERS[tag] - image_dsp.BASE
    if at + 4 > len(data):
        raise ValueError("image has no DSP boot pointer")
    pointer = int.from_bytes(data[at:at + 4], "big")
    decoded = image_dsp._upload(data, tag)
    container = None
    if image_dsp.BASE <= pointer < image_dsp.BASE + len(data):
        raw, offset = data, pointer - image_dsp.BASE
    else:
        raw, offset = image_dsp.unpack_payload(data, pointer), 0
        # Locate the exact loader entry whose checksums image_dsp validated.
        container = _packed_entries(data).get(pointer)
        if container is None:
            raise ValueError("packed upload must have one physical loader entry")
    try:
        records, _ = ab_records.records(raw, image_dsp.BASE + offset,
                                       len(raw) - offset)
    except (IndexError, SystemExit) as exc:
        raise ValueError("invalid DSP records") from exc
    if [(s, a, n) for s, a, n, _ in records] != [
            (s, a, len(words)) for s, a, words in decoded]:
        raise ValueError("decoded record layout disagrees with image bytes")
    return dict(pointer=pointer, raw=raw, records=records,
                decoded=decoded, container=container)


def verify_pair(baseline: Path, candidate: Path) -> dict:
    """Return a JSON-serializable receipt or raise ValueError on any extra change."""
    baseline, candidate = Path(baseline).resolve(), Path(candidate).resolve()
    before, after = baseline.read_bytes(), candidate.read_bytes()
    if len(before) != len(after):
        raise ValueError("MAIN OS image length changed")
    changed = []
    uploads = {}
    for tag in "AB":
        old, new = _upload(before, tag), _upload(after, tag)
        uploads[tag] = old, new
        if old["pointer"] != new["pointer"] or old["container"] != new["container"]:
            raise ValueError(f"payload {tag} placement or packed length changed")
        if old["records"] != new["records"]:
            raise ValueError(f"payload {tag} record layout changed")
        for (space, address, values), (_, _, replacements), (_, _, _, offset) in zip(
                old["decoded"], new["decoded"], old["records"]):
            changed.extend((tag, space, address + i, value, replacement, offset + 3 * i)
                           for i, (value, replacement) in enumerate(zip(values, replacements))
                           if value != replacement)
    if len(changed) != 1:
        raise ValueError(f"expected exactly one DSP word change; found {len(changed)}")
    tag, space, address, value, replacement, raw_offset = changed[0]
    if space != 0 or value != 8192 or replacement != 4096:
        raise ValueError("changed word is not the P-space 8192 -> 4096 literal")
    if tag == "A" and not image_dsp.SHARED[0] <= address < image_dsp.SHARED[1]:
        raise ValueError("core A private code is not BusDelay's shipping placement")
    old, new = uploads[tag]
    program = {}
    for sp, start, words in old["decoded"]:
        if sp == 0:
            for i, word in enumerate(words):
                if start + i in program:
                    raise ValueError("overlapping program upload records")
                program[start + i] = word
    # move #>imm,x0 / do x0,<NOP address> / nop. The DO end address is
    # inclusive: the assembled pad_end label contributes its previous word.
    signature = [program.get(address + i) for i in (-1, 0, 1, 2, 3)]
    if signature != [0x44f400, 8192, 0x06c400, address + 3, 0]:
        raise ValueError("changed literal lacks the exact single-NOP DO pad signature")
    expected_raw = bytearray(old["raw"])
    expected_raw[raw_offset:raw_offset + 3] = (4096).to_bytes(3, "little")
    if expected_raw != new["raw"]:
        raise ValueError("decoded upload contains changes outside the pad literal")
    normalized = bytearray(after)
    allowed = []
    if old["container"] is None:
        normalized[raw_offset:raw_offset + 3] = before[raw_offset:raw_offset + 3]
        allowed.append([raw_offset, raw_offset + 3])
    else:
        entry, blob, size = old["container"]
        allowed = [[blob, blob + size], [entry + 8, entry + 12],
                   [entry + 24, entry + 28]]
        for lo, hi in allowed:
            normalized[lo:hi] = before[lo:hi]
    if normalized != before:
        raise ValueError("MAIN OS contains changes outside the pad container/checksums")
    return dict(
        passed=True,
        baseline=dict(path=str(baseline), sha256=_sha(before)),
        candidate=dict(path=str(candidate), sha256=_sha(after)),
        image_bytes=len(before),
        differing_image_bytes=sum(a != b for a, b in zip(before, after)),
        physical_upload=tag, space="P", word_address=address,
        before_nops=value, after_nops=replacement,
        signature_words=signature,
        decoded_upload_differing_bytes=1,
        allowed_container_byte_ranges=allowed,
        all_other_image_bytes_identical=True,
        all_other_dsp_words_identical=True,
        hardware_timing_verified=False,
    )


def verify_label_pair(baseline: Path, candidate: Path,
                      before_name: str, after_name: str) -> dict:
    """Prove package relabelling changes only fixed-length C strings and hashes.

    Check every loader payload, including the ColdFire runtime. DSP uploads
    must remain completely identical even if a label-like byte sequence occurs
    in one. No compressed payload is accepted merely because it is a container.
    """
    old_name, new_name = before_name.encode("ascii"), after_name.encode("ascii")
    if (not 1 <= len(old_name) <= 15 or len(old_name) != len(new_name)
            or old_name == new_name or any(c < 32 or c > 126 for c in old_name + new_name)):
        raise ValueError("package names must differ and have equal lengths of 1..15 ASCII bytes")
    old_name += b"\0"
    new_name += b"\0"
    baseline, candidate = Path(baseline).resolve(), Path(candidate).resolve()
    before, after = baseline.read_bytes(), candidate.read_bytes()
    if len(before) != len(after):
        raise ValueError("labelled MAIN OS image length changed")
    for tag in "AB":
        if image_dsp._upload(before, tag) != image_dsp._upload(after, tag):
            raise ValueError(f"package label changed payload {tag}'s DSP upload")
    entries = _packed_entries(before)
    if entries != _packed_entries(after):
        raise ValueError("package label changed packed container layout")
    normalized = bytearray(after)
    replacements = []
    for destination, (entry, blob, size) in entries.items():
        old = image_dsp.unpack_payload(before, destination)
        new = image_dsp.unpack_payload(after, destination)
        if old == new:
            # An unchanged decoded payload does not license container changes.
            continue
        count = old.count(old_name)
        if not count or old.replace(old_name, new_name) != new:
            raise ValueError("packed payload contains changes beyond its package label")
        replacements.append(dict(packed_destination=destination, count=count))
        for lo, hi in ((blob, blob + size), (entry + 8, entry + 12),
                       (entry + 24, entry + 28)):
            normalized[lo:hi] = before[lo:hi]
    expected = bytearray(before)
    at = before.find(old_name)
    while at >= 0:
        if not any(blob <= at < blob + size for _, blob, size in entries.values()):
            expected[at:at + len(old_name)] = new_name
            replacements.append(dict(image_offset=at, count=1))
        at = before.find(old_name, at + len(old_name))
    if not replacements or normalized != expected:
        raise ValueError("MAIN OS contains changes beyond the package label/verified containers")
    return dict(passed=True, before_name=before_name, after_name=after_name,
                baseline=dict(path=str(baseline), sha256=_sha(before)),
                candidate=dict(path=str(candidate), sha256=_sha(after)),
                label_replacements=replacements,
                differing_image_bytes=sum(a != b for a, b in zip(before, after)),
                dsp_uploads_identical=True, all_other_image_bytes_identical=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--labels", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="verify label-only repackaging instead of the wait change")
    args = parser.parse_args()
    try:
        receipt = (verify_label_pair(args.baseline, args.candidate, *args.labels)
                   if args.labels else verify_pair(args.baseline, args.candidate))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"DMA wait pair refused: {exc}\n")
    result = json.dumps(receipt, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result)
    print(result, end="")


if __name__ == "__main__":
    main()
