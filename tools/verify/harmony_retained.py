"""Inspection helpers for the two Harmony retained layouts, not musical oracles."""
from verify_midi_sram import BASE, OFFSETS

def track_layout(m):
    return 'hd_track_read_c' in m.sym

def snapshot(m):
    if track_layout(m):
        data=bytes(m.uc.mem_read(BASE,16*0x8ed8))
        return bytes(data[o] for o in OFFSETS)
    return bytes(m.uc.mem_read(m.sym['hd_nv_base'],10400))

def install(m,data):
    if track_layout(m):
        assert len(data)==16384
        for i in range(0,len(data),2):m.uc.mem_write(BASE+OFFSETS[i],bytes(data[i:i+2]))
    else:m.uc.mem_write(m.sym['hd_nv_base'],bytes(data))

def committed(m):
    if track_layout(m):return int.from_bytes(m.uc.mem_read(BASE+OFFSETS[0],2),'big') & 0xfc00 == 0xac00
    return bytes(m.uc.mem_read(m.sym['hd_nv_base'],4))==b'HDN3'


def raw_p2(records, bank=0):
    """Independent upstream P2NV fixture; no compression implementation needed."""
    import struct
    entries=[(index<<7)|value for index,value in records]
    return struct.pack('>4sIII',b'P2NV',bank,len(entries),sum(entries)&0xffffffff)+b''.join(
        entry.to_bytes(3,'big') for entry in entries)
