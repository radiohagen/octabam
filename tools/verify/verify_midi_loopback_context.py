#!/usr/bin/env python3
"""MIDI routing must not inherit retained audio voices or a future UI Part.

Execute the linked routing code, then observe routes and note release. The
native panel transition companion verifies how stock firmware sets the state.
"""
import verify_midi_loopback as lb
from verify_midi_loopback_settings import field, B, BS


def main():
    m = lb.Machine()
    # Different destinations in every context and on adjacent MIDI tracks.
    for bank in (0, 15):
        for part in range(4):
            for track in range(8):
                m.put(field(bank, part, track), 4*((part+track+bank) % 3), 1)
    cases = 0
    for bank in (0, 15):
        for part in range(4):
            m.u.mem_write(0x8000666e, bytes([bank]*8))
            m.u.mem_write(0x80006676, bytes([part]*8))
            m.put(0x46c7a934, (part+1) % 4, 1)
            # UI selects another bank/Part; audio can retain any Part or none.
            m.put(0x46c82456, B+(15-bank)*BS)
            m.put(0x100b14cf, (part+1) % 4, 1)
            for audio_part in (0, 1, 2, 3, 255):
                m.put(0x80001828, 15-bank, 1)
                m.put(0x80001829, (part+2) % 4, 1)
                m.u.mem_write(0x8000182a, bytes([15-bank]*8))
                m.u.mem_write(0x80001832, bytes([audio_part]*8))
                m.call('lb_part_sync')
                expected = bytes((part+t+bank) % 3 for t in range(8))
                actual = bytes(m.u.mem_read(m.sym['lb_routes'], 8))
                assert actual == expected, (bank, part, audio_part, actual, expected)
                cases += 1
    print(f'[ok] {cases} MIDI contexts vs conflicting audio/UI states, all eight tracks and EXT/INT/BOTH')

    # Queued/UI-only changes must not release current notes. An actual MIDI
    # context switch must release the old identity, even with the same route.
    for new_route in (0, 1, 2):
        for track in range(8):
            channel = track
            m.u.mem_write(0x8000666e, bytes(8))
            m.u.mem_write(0x80006676, bytes(8))
            m.put(field(0, 0, track), 4, 1)
            m.put(field(0, 1, track), 4*new_route, 1)
            m.call('lb_part_sync')
            assert m.capture((0x90|channel, 84, 100), track=track) == 0
            assert m.next() == bytes((0x90|channel, 84, 100))
            m.put(0x100b14cf, 1, 1)
            m.put(0x80001832+track, 1, 1)
            m.call('lb_part_sync')
            assert m.get('lb_internal_held') == 1, 'UI/audio change released MIDI note early'
            m.put(0x80006676+track, 1, 1)
            m.call('lb_part_sync')
            assert m.next() == bytes((0x80|channel, 84, 0))
            assert m.get('lb_internal_held') == 0
            assert m.get(m.sym['lb_routes']+track, 1) == new_route
            assert m.capture((0x80|channel, 84, 0), 0x4009f8c2, track=track) == 0
    print('[ok] queued UI/audio state cannot release notes; actual Part changes release old notes once on every track')

    # Each MIDI track can retain a different native context. Route by its
    # own setup, not another track or a global pattern/setup-message latch.
    for track in range(8):
        bank, part = (15 if track % 2 else 0), track % 4
        m.put(0x8000666e+track, bank, 1)
        m.put(0x80006676+track, part, 1)
        m.put(field(bank, part, track), 4*(track % 3), 1)
    m.call('lb_part_sync')
    assert bytes(m.u.mem_read(m.sym['lb_routes'], 8)) == bytes(t % 3 for t in range(8))
    # Before the first MIDI trig, stock uses its applied engine context.
    m.u.mem_write(0x8000666e, bytes([255]*8))
    m.u.mem_write(0x80006676, bytes([255]*8))
    m.put(0x80001828, 0, 1); m.put(0x80001829, 2, 1)
    for track in range(8):
        m.put(field(0, 2, track), 4*(track % 3), 1)
    m.call('lb_part_sync')
    assert bytes(m.u.mem_read(m.sym['lb_routes'], 8)) == bytes(t % 3 for t in range(8))
    print('[ok] independent MIDI track contexts and pre-trig applied-context fallback')

    for bank, part in ((16, 0), (255, 0), (0, 4), (0, 255)):
        m.put(0x80001828, bank, 1)
        m.put(0x80001829, part, 1)
        m.call('lb_part_sync')
        assert bytes(m.u.mem_read(m.sym['lb_routes'], 8)) == bytes(8)
    print('[ok] invalid MIDI context falls back to EXT instead of indexing another Part')


if __name__ == '__main__':
    main()
