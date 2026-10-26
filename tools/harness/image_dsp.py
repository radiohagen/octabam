"""Dump the DSP uploads reached by a supplied image's own boot pointers.

Unlike the development dumper, this never reads out/dsp/*.json. Window code
comes from the image's checksum-verified pre-boot upload, so two frozen images
cannot silently execute whichever window source was built most recently.
Demand-loaded code is intentionally absent until firmware loads it.
"""
from pathlib import Path
import struct

import ab_records
from ghidra.depack import depack
from remix.platform_build import roll

BASE = ab_records.BASE
BOOT_POINTERS = {"A": 0x40001e8e, "B": 0x40001ed4}
SHARED = (0x30000, 0x40000)


def _records(data: bytes, offset: int):
    """Decode a bounded stock upload, preserving its record order."""
    if not 0 <= offset < len(data):
        raise ValueError("DSP upload pointer lies outside its data")
    try:
        records, term = ab_records.records(data, BASE + offset, len(data) - offset)
    except (IndexError, SystemExit) as exc:
        raise ValueError("truncated or unterminated DSP upload") from exc
    if term + 3 > len(data):
        raise ValueError("truncated DSP upload terminator")
    result = []
    for space, address, count, at in records:
        if at + count * 3 > term:
            raise ValueError("DSP record extends past the upload terminator")
        words = [int.from_bytes(data[i:i+3], "little")
                 for i in range(at, at + count * 3, 3)]
        result.append((space, address, words))
    return result


def unpack_payload(image: bytes, destination: int) -> bytes:
    """Return the image's unique, length/checksum-verified loader payload.

    The destination can name either a DSP upload or the ColdFire runtime.
    No ambient build artifact supplies bytes to this extraction.
    """
    entries = set()
    start = 0
    while True:
        blob = image.find(b"OCTAGKA3", start)
        if blob < 0:
            break
        pointer = struct.pack(">I", BASE + blob)
        entry_at = image.find(pointer)
        while entry_at >= 0:
            if entry_at + 32 <= len(image):
                entry = struct.unpack_from(">8I", image, entry_at)
                if entry[4] == destination:
                    entries.add(entry)
            entry_at = image.find(pointer, entry_at + 1)
        start = blob + 8
    if len(entries) != 1:
        raise ValueError(f"DSP boot pointer 0x{destination:08x} has {len(entries)} matching loader payloads")
    pointer, size, packed_hash, _stage, _dst, raw_size, raw_hash, _backup = entries.pop()
    offset = pointer - BASE
    if size < 12 or offset + size > len(image):
        raise ValueError("packed DSP payload length lies outside the image")
    blob = image[offset:offset+size]
    if roll(blob[4:]) != packed_hash:
        raise ValueError("packed DSP payload checksum mismatch")
    if int.from_bytes(blob[8:12], "big") != raw_size:
        raise ValueError("DSP payload header/table lengths disagree")
    try:
        raw = depack(blob[4:])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"invalid packed DSP upload: {exc}") from exc
    if len(raw) != raw_size:
        raise ValueError("depacked DSP payload length mismatch")
    if roll(raw) != raw_hash:
        raise ValueError("depacked DSP payload checksum mismatch")
    return raw


def _packed_upload(image: bytes, destination: int):
    """Decode the payload at exactly the address the DSP boot call reads."""
    return _records(unpack_payload(image, destination), 0)


def _upload(image: bytes, payload: str):
    at = BOOT_POINTERS[payload] - BASE
    if at + 4 > len(image):
        raise ValueError("image has no DSP boot pointer")
    pointer = int.from_bytes(image[at:at+4], "big")
    if BASE <= pointer < BASE + len(image):
        return _records(image, pointer - BASE)
    return _packed_upload(image, pointer)


def dump_mem(image, out, payload="A"):
    """Write dsp_host's flat memory format using only this image; return Path.

    Both cores see A's shared-window P upload on hardware. dsp_host's P
    spaces are private, so B also receives those records (only their shared
    portion). Private A P/X/Y records are never copied to B.
    """
    payload = payload.upper()
    if payload not in BOOT_POINTERS:
        raise ValueError(f"unknown DSP payload {payload!r}")
    data = Path(image).read_bytes()
    records = _upload(data, payload)
    if payload == "B":
        for space, address, words in _upload(data, "A"):
            lo, hi = max(address, SHARED[0]), min(address + len(words), SHARED[1])
            if space == 0 and lo < hi:
                records.append((space, lo, words[lo-address:hi-address]))
    body = bytearray()
    for space, address, words in records:
        body += struct.pack("<BII", space, address, len(words))
        body += struct.pack("<" + "I" * len(words), *words)
    body += struct.pack("<BII", 255, 0, 0)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"payload {payload}: {len(records)} image-bound records, "
          f"{sum(len(w) for _, _, w in records):,} words -> {out}")
    return out
