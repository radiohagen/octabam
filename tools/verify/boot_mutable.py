"""Validate module-owned boot data declarations against the actual linked units.

This accounts for permitted writes, not their semantic correctness. A module's
own gates must verify values. Undeclared bytes retain the existing boot budget.
"""
from remix import platform_build


def resolve_ranges(modules, layout, work, raw):
    declarations = [(m.key, u) for m in modules for u in m.linked if u.boot_mutable]
    if not declarations:
        return []
    placed = platform_build._map_sections(work / 'runtime.map')
    ranges = []
    for owner, unit in declarations:
        indices = [i for i, row in enumerate(layout['units'])
                   if row[:2] == [owner, unit.label]]
        if len(indices) != 1:
            raise ValueError(f'{owner}/{unit.label}: missing or ambiguous boot-data owner')
        obj = work / f'{indices[0]:02d}_{unit.label}.o'
        symbols = platform_build._object_symbols(obj, work)
        for name, size in unit.boot_mutable:
            matches = [(section, offset) for symbol, section, offset in symbols if symbol == name]
            if len(matches) != 1:
                raise ValueError(f'{unit.label}.{name}: symbol must be defined once by its owner')
            section, offset = matches[0]
            extent = placed.get((str(obj), section))
            if extent is None or not 0 <= offset < offset + size <= extent[1]:
                raise ValueError(f'{unit.label}.{name}: boot data exceeds its owning section')
            start = extent[0] + offset
            lo = start - layout['base']
            if not 0 <= lo < lo + size <= len(raw):
                raise ValueError(f'{unit.label}.{name}: boot data exceeds the runtime payload')
            if raw[lo:lo + size] != bytes(size):
                raise ValueError(f'{unit.label}.{name}: boot data must start zeroed')
            if any(start < end and begin < start + size for begin, end in ranges):
                raise ValueError(f'{unit.label}.{name}: overlapping boot data declarations')
            ranges.append((start, start + size))
    return sorted(ranges)


def compare_runtime(base, expected, actual, ranges, budget=64):
    changed = [base + i for i, (a, b) in enumerate(zip(expected, actual)) if a != b]
    mutable = sum(any(lo <= address < hi for lo, hi in ranges) for address in changed)
    other = len(changed) - mutable
    return len(actual) == len(expected) and other <= budget, mutable, other
