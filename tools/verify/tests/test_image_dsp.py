"""Image-bound DSP extraction, using generated data and no firmware fixture."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import toolpath  # noqa: E402,F401
import image_dsp
from ab_records import ot_record
from remix import pack
from remix.platform_build import roll

BASE = image_dsp.BASE


def upload(records):
    # Both optional stock headers, then records and a 24-bit terminator.
    return bytes.fromhex('030000000000040000000000') + b''.join(
        ot_record(space, addr, words) for space, addr, words in records) + b'\xff\xff\xff'


def flat(path):
    data, pos, result = path.read_bytes(), 0, []
    while True:
        space, addr, count = struct.unpack_from('<BII',data,pos);pos += 9
        if space == 255:
            assert pos == len(data)
            return result
        words = list(struct.unpack_from('<'+'I'*count,data,pos));pos += 4*count
        result.append((space,addr,words))


def pointer(image, tag, value):
    at = image_dsp.BOOT_POINTERS[tag]-BASE
    image[at:at+4] = struct.pack('>I',value)


def direct(a, b):
    image=bytearray(0x3000)
    for tag, at, data in (('A',0x2400,a),('B',0x2800,b)):
        image[at:at+len(data)]=data
        pointer(image,tag,BASE+at)
    return image


def packed(a, b):
    image=bytearray(0x3000)
    locations=[]
    for i,(tag,raw) in enumerate((('A',a),('B',b))):
        with patch.object(pack,'_cache_on',return_value=False):
            blob=b'OCTAGKA3'+struct.pack('>I',len(raw))+pack.pack(raw,4096)
        at=len(image); image += blob
        dest=0x48b00000+i*0x100000
        entry=0x2400+i*32
        struct.pack_into('>8I',image,entry,BASE+at,len(blob),roll(blob[4:]),
                         dest+0x80000,dest,len(raw),roll(raw),0)
        pointer(image,tag,dest)
        locations.append((entry,at,len(blob)))
    return image,locations


class ImageDspTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.a=[(0,0x100,[0x123456,0xabcdef]),(1,0x200,[7]),
                (0,0x2ffff,[11,12,13]),(0,0x3ffff,[14,15]),(2,0x30100,[99])]
        self.b=[(0,0x500,[0x654321]),(1,0x210,[8])]
        self.shared=[(0,0x30000,[12,13]),(0,0x3ffff,[14])]
    def tearDown(self):self.tmp.cleanup()
    def run_dump(self,image,tag):
        src=self.root/'image.bin';src.write_bytes(image)
        return flat(image_dsp.dump_mem(src,self.root/f'{tag}.mem',tag))
    def test_direct_boot_pointers_and_shared_program(self):
        image=direct(upload(self.a),upload(self.b))
        self.assertEqual(self.run_dump(image,'A'),self.a)
        self.assertEqual(self.run_dump(image,'B'),self.b+self.shared)
    def test_packed_uploads_match_direct(self):
        image,_=packed(upload(self.a),upload(self.b))
        self.assertEqual(self.run_dump(image,'A'),self.a)
        self.assertEqual(self.run_dump(image,'B'),self.b+self.shared)
    def test_generic_payload_is_not_parsed_as_dsp_records(self):
        raw=bytes(range(256))+b'ColdFire runtime, not a DSP upload'
        image,_=packed(raw,upload(self.b))
        self.assertEqual(image_dsp.unpack_payload(image,0x48b00000),raw)
    def test_other_destination_is_not_a_fallback(self):
        image,_=packed(upload(self.a),upload(self.b));pointer(image,'A',0x48d00000)
        with self.assertRaisesRegex(ValueError,'0 matching'):
            self.run_dump(image,'A')
    def test_packed_checksum_rejected(self):
        image,loc=packed(upload(self.a),upload(self.b));image[loc[0][1]+12] ^= 1
        with self.assertRaisesRegex(ValueError,'packed DSP payload checksum'):
            self.run_dump(image,'A')
    def test_raw_checksum_rejected(self):
        image,loc=packed(upload(self.a),upload(self.b));image[loc[0][0]+24] ^= 1
        with self.assertRaisesRegex(ValueError,'depacked DSP payload checksum'):
            self.run_dump(image,'A')
    def test_length_rejected(self):
        image,loc=packed(upload(self.a),upload(self.b));image[loc[0][0]+23] ^= 1
        with self.assertRaisesRegex(ValueError,'lengths disagree'):
            self.run_dump(image,'A')
    def test_packed_bounds_rejected(self):
        image,loc=packed(upload(self.a),upload(self.b));struct.pack_into('>I',image,loc[0][0]+4,len(image))
        with self.assertRaisesRegex(ValueError,'length lies outside'):
            self.run_dump(image,'A')
    def test_unterminated_record_rejected(self):
        image=bytearray(0x2000);pointer(image,'A',BASE+len(image)-9)
        image[-9:]=bytes.fromhex('000000000100ffffff')
        with self.assertRaisesRegex(ValueError,'unterminated'):
            self.run_dump(image,'A')
    def test_invalid_payload_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown'):
            self.run_dump(bytes(0x2000),'C')


if __name__=='__main__':unittest.main()
