"""Fault injection for the opt-in DMA experiment's image boundary."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import toolpath  # noqa: E402,F401
import image_dsp  # noqa: E402
from ab_records import ot_record  # noqa: E402
from remix import pack  # noqa: E402
from remix.platform_build import roll  # noqa: E402
from verify_dma_wait import verify_pair, verify_label_pair  # noqa: E402
from build_dma_wait_test import half_wait, PAD  # noqa: E402


def upload(address, count, *, opcode=0x44f400, target_delta=4, trailer=b""):
    words = [opcode, count, 0x06c400, address + target_delta, 0]
    return (bytes.fromhex("030000000000040000000000")
            + ot_record(0, address, words) + b"\xff\xff\xff" + trailer)


def image(count, *, packed=False, address=None, **kwargs):
    address = (0x35800 if packed else 0x100) if address is None else address
    pad, inert = upload(address, count, **kwargs), upload(0x500, 7)
    data = bytearray(0x3000)
    for index, (tag, raw) in enumerate(zip("AB", (pad, inert) if packed else (inert, pad))):
        entry = 0x2400 + index * 0x400
        if packed and tag == "A":
            with patch.object(pack, "_cache_on", return_value=False):
                blob = b"OCTAGKA3" + struct.pack(">I", len(raw)) + pack.pack(raw, 4096)
            at, destination = len(data), 0x48b00000
            data.extend(blob)
            struct.pack_into(">8I", data, entry, image_dsp.BASE + at, len(blob),
                             roll(blob[4:]), destination + 0x80000,
                             destination, len(raw), roll(raw), 0)
        else:
            data[entry:entry + len(raw)] = raw
            destination = image_dsp.BASE + entry
        at = image_dsp.BOOT_POINTERS[tag] - image_dsp.BASE
        struct.pack_into(">I", data, at, destination)
    return data


def labelled_image(name, *, extra=b"unchanged", count=4096):
    data = image(count)
    raw = b"runtime prefix\0" + name.encode("ascii") + b"\0" + extra
    with patch.object(pack, "_cache_on", return_value=False):
        blob = b"OCTAGKA3" + struct.pack(">I", len(raw)) + pack.pack(raw, 4096)
    at, entry, destination = len(data), 0x2600, 0x48c00000
    data.extend(blob)
    struct.pack_into(">8I", data, entry, image_dsp.BASE + at, len(blob),
                     roll(blob[4:]), destination + 0x80000, destination,
                     len(raw), roll(raw), 0)
    return data


class DmaWait(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def verify(self, before, after):
        baseline, candidate = self.root / "base.bin", self.root / "half.bin"
        baseline.write_bytes(before)
        candidate.write_bytes(after)
        return verify_pair(baseline, candidate)

    def test_direct_and_packed_exact_pad_change(self):
        for packed in (False, True):
            with self.subTest(packed=packed):
                receipt = self.verify(image(8192, packed=packed), image(4096, packed=packed))
                self.assertTrue(receipt["passed"])
                self.assertTrue(receipt["all_other_image_bytes_identical"])
                self.assertEqual(receipt["decoded_upload_differing_bytes"], 1)
                self.assertFalse(receipt["hardware_timing_verified"])

    def test_no_change_wrong_count_and_reversed_pair(self):
        for old, new in ((8192, 8192), (8192, 0), (8192, 2048), (4096, 8192)):
            with self.subTest(old=old, new=new), self.assertRaises(ValueError):
                self.verify(image(old), image(new))

    def test_instruction_operand_and_loop_end_are_pinned(self):
        for wrong in ({"opcode": 0x45f400}, {"target_delta": 5}):
            with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, "signature"):
                self.verify(image(8192, **wrong), image(4096, **wrong))

    def test_private_core_a_is_not_the_delay(self):
        with self.assertRaisesRegex(ValueError, "core A private"):
            self.verify(image(8192, packed=True, address=0x100),
                        image(4096, packed=True, address=0x100))

    def test_unrelated_coldfire_byte_is_not_hidden_by_the_packed_allowance(self):
        for packed in (False, True):
            candidate = image(4096, packed=packed)
            candidate[0x123] ^= 1
            with self.subTest(packed=packed), self.assertRaises(ValueError):
                self.verify(image(8192, packed=packed), candidate)

    def test_second_dsp_word_is_rejected(self):
        candidate = image(4096)
        # The NOP is the fifth word after the 12-byte header and record header.
        candidate[0x2800 + 12 + 9 + 4 * 3] = 1
        with self.assertRaisesRegex(ValueError, "one DSP word"):
            self.verify(image(8192), candidate)

    def test_decoded_trailing_payload_bytes_cannot_hide_inside_the_allowance(self):
        before = image(8192, packed=True, trailer=b"fixed")
        after = image(4096, packed=True, trailer=b"fixee")
        with self.assertRaisesRegex(ValueError, "outside the pad literal"):
            self.verify(before, after)

    def test_packed_corruption_and_image_truncation_are_rejected(self):
        candidate = image(4096, packed=True)
        candidate[0x2400 + 24] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.verify(image(8192, packed=True), candidate)
        with self.assertRaisesRegex(ValueError, "length"):
            self.verify(image(8192), image(4096)[:-1])

    def test_generator_requires_one_complete_unchanged_pad(self):
        source = "other code\n" + PAD + "more code\n"
        self.assertEqual(half_wait(source), source.replace("$2000", "$1000"))
        for drifted in ("no pad", PAD + PAD, PAD.replace("do      x0", "do      y0")):
            with self.subTest(drifted=drifted), self.assertRaises(ValueError):
                half_wait(drifted)

    def verify_label(self, before, after):
        baseline, candidate = self.root / "named-old.bin", self.root / "named-new.bin"
        baseline.write_bytes(before)
        candidate.write_bytes(after)
        return verify_label_pair(baseline, candidate, "BUS DMA8K", "BUS DMA4K")

    def test_package_label_changes_only_name_in_verified_coldfire_payload(self):
        receipt = self.verify_label(labelled_image("BUS DMA8K"), labelled_image("BUS DMA4K"))
        self.assertTrue(receipt["dsp_uploads_identical"])
        self.assertEqual(receipt["label_replacements"],
                         [dict(packed_destination=0x48c00000, count=1)])

    def test_label_cannot_hide_dsp_runtime_or_unpacked_changes(self):
        baseline = labelled_image("BUS DMA8K")
        runtime = labelled_image("BUS DMA4K", extra=b"unchangEd")
        dsp = labelled_image("BUS DMA4K", count=8192)
        external = labelled_image("BUS DMA4K")
        external[0x123] = 1
        for candidate in (runtime, dsp, external):
            with self.subTest(candidate=candidate[:5]), self.assertRaises(ValueError):
                self.verify_label(baseline, candidate)

    def test_label_requires_complete_c_string(self):
        with self.assertRaises(ValueError):
            self.verify_label(labelled_image("BUS DMA8K-extra"), labelled_image("BUS DMA4K-extra"))


if __name__ == "__main__":
    unittest.main()
