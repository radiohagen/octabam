"""Resolve explicitly declared resident-to-runtime links without moving entries."""


def resolve(unit, runtime_tables):
    values = {}
    for name, provider, symbol in unit.runtime_refs:
        if symbol not in runtime_tables.get(provider, {}):
            raise ValueError(f"{unit.label}: runtime reference {name} needs "
                             f"{provider}.{symbol}, which the runtime does not define")
        values[name] = runtime_tables[provider][symbol]
    return values


def check_layout(label, before, before_exports, after, after_exports):
    """Later units may already reference these exports or occupy adjacent space."""
    if len(before) != len(after):
        raise ValueError(f"{label}: runtime reference link changed resident size "
                         f"from {len(before)} to {len(after)} bytes")
    if before_exports != after_exports:
        raise ValueError(f"{label}: runtime reference link moved resident exports")


def own_exports(exports, imports):
    """Linker --defsym imports also appear in nm; never publish them as owners.

    In particular a resident relink must not overwrite final runtime descriptor
    addresses with the staging addresses supplied during its initial link.
    """
    return {name: value for name, value in exports.items() if name not in imports}
