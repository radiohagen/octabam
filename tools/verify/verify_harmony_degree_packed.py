#!/usr/bin/env python3
"""Lossless packed storage against an independent bitstream oracle.

Executes the linked ColdFire codec, including every legal step tuple and
invalid data with valid checksums. Native edits after a retained checkpoint
must remain distinguishable from KEY changes and edit reversions.
"""
import json
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import *
from verify_harmony_degree_integration import DegreeMachine, ROOT
from midi_machine import InterruptMaskTrace

PAYLOAD = 10368
RETAINED = PAYLOAD + 32
LANE = 81
NV = 0x100fd560


def oracle(roots, qualities):
    result = bytearray()
    for lane in range(128):
        r = roots[lane*131:(lane+1)*131]
        state, scale = r[128:130]
        result.append(state*84+scale)
        tokens = []
        for step in range(64):
            d, n, q = r[step], r[64+step], qualities[lane*64+step]
            tokens.append((84 if d == 255 else d)*9+(8 if q == 255 else q))
        # A lane is one 640-bit big-endian integer, independent of the
        # firmware's streaming reservoir and byte-write algorithm.
        result.extend(sum(v << (10*(63-i)) for i, v in enumerate(tokens)).to_bytes(80, 'big'))
    return bytes(result)


def mirror(degree):
    return 255 if degree == 255 else max(0,min(127,12*(degree//7-1)+(0,2,4,5,7,9,11)[degree%7]))


def main():
    from remix.registry import modules
    m = DegreeMachine(); u = m.uc; s = m.sym
    if 'hd_track_read_c' in s:
        from verify_harmony_track_retention import main as track_main
        track_main()
        return
    global NV
    NV = s['hd_nv_base']
    assert NV in (0x100fd560, 0x100f8620)
    p2_size = 20 if NV == 0x100f8620 else 15464
    assert 0x100f8600+p2_size <= NV
    # The shared layout leaves 12 bytes here. A fixed 16-byte test guard
    # would itself overwrite the last four bytes of the P2 header.
    prefix_guard = min(16, NV - (0x100f8600+p2_size))
    assert NV+RETAINED <= (0x100fbdf0 if NV == 0x100f8620 else 0x100ffe00)
    for start, length, _ in modules()['KITS'].claims.sram:
        assert NV+RETAINED <= start or start+length <= NV
    m.call('ch_lock_init')
    h, q = s['hd_banks'], s['ch_lock_table']
    scratch = 0x48000000
    u.mem_map(scratch, 0x20000)
    p = scratch+32
    count = banks = 0
    for state in range(3):
        pairs = ([(255, 255)] if state == 0 else
                 [(255, n) for n in range(128)]+[(255, 255)] if state == 1 else
                 [(d, mirror(d)) for d in range(84)]+[(255, 255)])
        tuples = [(d, n, quality) for d, n in pairs for quality in (*range(8), 255)]
        count += len(tuples)
        for offset in range(0, len(tuples), 8192):
            roots = bytearray(); qualities = bytearray()
            for lane in range(128):
                chunk = [tuples[(offset+lane*64+step) % len(tuples)] for step in range(64)]
                roots.extend(bytes(d for d, _, _ in chunk)+bytes(n for _, n, _ in chunk))
                roots.extend((state, lane % 84, 255 if state == 0 else lane % 64))
                qualities.extend(quality for _, _, quality in chunk)
            expected = oracle(roots, qualities)
            u.mem_write(h, bytes(roots)); u.mem_write(q, bytes(qualities))
            u.mem_write(scratch, b'\xa5'*(PAYLOAD+64))
            assert m.c('hd_pack_c', h, q, p) == 1
            assert bytes(u.mem_read(p, PAYLOAD)) == expected
            assert u.mem_read(scratch, 32) == b'\xa5'*32
            assert u.mem_read(p+PAYLOAD, 32) == b'\xa5'*32
            u.mem_write(h, b'\xcc'*16768); u.mem_write(q, b'\xcc'*8192)
            assert m.c('hd_unpack_c', h, q, p) == 1
            for lane in range(128):
                roots[lane*131+130] = 255
                if state != 2: roots[lane*131+64:lane*131+128] = bytes([255])*64
            assert bytes(u.mem_read(h, 16768)) == roots
            assert bytes(u.mem_read(q, 8192)) == qualities
            banks += 1
    print(f'[ok] {count} legal CHRD/DEG/NOTE tuples; {banks} dense bank round trips', flush=True)

    # Every metadata position rejects a reserved byte without partial output.
    good = bytes(u.mem_read(p, PAYLOAD))
    before_h, before_q = bytes(u.mem_read(h, 16768)), bytes(u.mem_read(q, 8192))
    # An impossible runtime snapshot must fail, never be silently discarded.
    u.mem_write(h+64, bytes(((before_h[64]+1) % 128,)))
    assert m.c('hd_pack_c', h, q, p) == 0
    u.mem_write(h, before_h)
    malformed = []
    for lane in range(128):
        data = bytearray(good); data[lane*LANE] = 252+lane % 4
        malformed.append(data)
    for state, token in ((0, 0), (1, 0), (2, 765), (2, 0x3ff)):
        data = bytearray(good); data[0] = state*84
        first = int.from_bytes(data[1:81], 'big')
        first = (first & ((1 << (10*63))-1)) | (token << (10*63))
        data[1:81] = first.to_bytes(80, 'big'); malformed.append(data)
    for data in malformed:
        u.mem_write(p, bytes(data))
        assert m.c('hd_unpack_c', h, q, p) == 0
        assert bytes(u.mem_read(h, 16768)) == before_h
        assert bytes(u.mem_read(q, 8192)) == before_q

    # Regression: the checkpoint remembers the exact native note, even after
    # KEY changes. A one-bit equal/different flag cannot handle these cases.
    bank = 0x400e21e0; native = bank+0x4900
    u.mem_write(bank, b"\xff"*0x9b340)
    u.mem_write(bank+0x8ed80+0x4e2+3, b"\0")
    m.c('hd_bank_reset_c', 0); u.mem_write(q, b'\xff'*8192)
    u.mem_write(bank+0x8e57, b'\0')
    u.mem_write(bank+0x8ed80+0x4e2+5, b'\x01')
    u.mem_write(bank+0x8ed80+0x4e2+17, b'\x06')  # incoming D minor
    r = bytearray(b'\xff'*128+bytes((2, 60, 255)))  # detached C minor
    r[0] = 35; r[64] = 48
    p2_reserved = bytes(i % 251 for i in range(p2_size))
    u.mem_write(0x100f8600, p2_reserved)
    regressions = []
    for at_save, at_restore, want in ((48, 48, 35), (48, 55, 38), (55, 48, 35)):
        u.mem_write(h, bytes(r)); u.mem_write(native, bytes((at_save,)))
        u.mem_write(NV-prefix_guard, b'\xa5'*prefix_guard)
        u.mem_write(NV+RETAINED, b'\x5a'*64)
        m.c('hd_nv_save_c', 0)
        assert u.mem_read(NV, 4) == b'HDN3'
        u.mem_write(native, bytes((at_restore,)))
        m.c('hd_bank_reset_c', 0)
        assert m.c('hd_nv_restore_c', 0) == 1
        actual = m.c('hd_degree_c', 0, 0, 0, 0)
        assert actual == want, (at_save, at_restore, want, actual, list(u.mem_read(h,131)), m.c('hd_scale_c',0,0,0))
        assert u.mem_read(NV-prefix_guard, prefix_guard) == b'\xa5'*prefix_guard
        assert u.mem_read(NV+RETAINED, 64) == b'\x5a'*64
        # Engine-side conversion invalidates first; the UI boundary restores
        # a complete checkpoint without running bulk work inside that mask.
        assert u.mem_read(NV, 4) == bytes(4)
        m.c('hd_nv_poll_c')
        assert u.mem_read(NV, 4) == b'HDN3'
        assert bytes(u.mem_read(0x100f8600, p2_size)) == p2_reserved
        regressions.append((at_save, at_restore, want))

    # Simulate a preempting saver at the first payload write. Pause before
    # its next instruction, execute the nested call on a separate stack,
    # then resume the exact saved CPU context. The outer owner must retry;
    # no valid magic is visible while it is still writing the payload.
    watch = False; pending = False; interrupted = False; writes = 0
    trace = InterruptMaskTrace(u)
    def written(uc, access, address, size, value, data):
        nonlocal pending, writes
        if watch and NV+32 <= address < NV+RETAINED:
            assert trace.ipl == 0, 'bulk packing masked interrupts'
            assert u.mem_read(NV, 4) == bytes(4), 'payload changed after commit'
            writes += 1
            if not interrupted: pending = True
    def inspect(uc, pc, size, data):
        if watch:
            trace.before(pc)
            if pending: uc.emu_stop()
    u.hook_add(UC_HOOK_MEM_WRITE, written); u.hook_add(UC_HOOK_CODE, inspect)
    u.mem_write(m.stack, m.done.to_bytes(4, 'big'))
    u.mem_write(m.stack+4, bytes(4))
    u.reg_write(UC_M68K_REG_A7, m.stack); u.reg_write(UC_M68K_REG_SR, 0x2000)
    m.arrival = None; watch = True
    u.emu_start(s['hd_nv_save_c'], 0, count=30000000)
    assert pending
    saved_context = u.context_save(); interrupted = True; pending = False; watch = False
    outer_stack = m.stack; m.stack = 0x4700c000
    u.mem_write(q+8191, b'\x06')
    m.c('hd_nv_save_c', 0)
    assert u.mem_read(NV, 4) == bytes(4)
    m.stack = outer_stack; u.context_restore(saved_context)
    m.arrival = None; trace.ipl = 0; watch = True
    u.emu_start(u.reg_read(UC_M68K_REG_PC), 0, count=30000000)
    watch = False
    assert m.arrival == m.done and writes >= PAYLOAD*2, (m.arrival, writes)
    u.mem_write(q+8191, b'\xff')
    assert m.c('hd_nv_restore_c', 0) == 1 and u.mem_read(q+8191, 1) == b'\x06'

    result = dict(legal_step_tuples=count, dense_round_trips=banks,
                  malformed_payloads_rejected=len(malformed), native_edit_regressions=regressions,
                  retained_bytes=RETAINED, retained_saving=24992-RETAINED,
                  preempting_save='retried without intermediate commit', bulk_retention_unmasked=True,
                  reservation_guards='unchanged', hardware_tested=False)
    result['dedicated_p2_bytes'] = p2_size
    result['protected_pool_bytes'] = 15448 if NV == 0x100f8620 else 0
    result['midi_scenes_retained_bytes'] = 16400 if NV == 0x100f8620 else 0
    result['shared_region_spare_bytes'] = 30720-p2_size-RETAINED-result['midi_scenes_retained_bytes']
    out = ROOT/'out/harmony-degrees'; out.mkdir(parents=True, exist_ok=True)
    (out/'packed.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
