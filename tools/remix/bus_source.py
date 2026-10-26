"""Optional bus transport/routing edits, shared by the builder and pricer.

Keep each module's asserted source edits beside that module. Apply transport
before return routing, before either source's memory-address substitutions.
Unselected modules leave the source byte-for-byte unchanged.
"""
from remix import registry


def transform(name, src, remix):
    if src is None or name not in ("SEND", "REVERB SERVER", "DELAY SERVER"):
        return src
    for key in ("POST FADER", "RETURNS"):
        if key in remix.modules:
            module = registry.by_key(key)
            path = registry.MODULES_DIR / module.name / "engine.py"
            helper = registry._exec(path, f"bus_source_{module.name}")
            src = helper.transform(name, src)
    return src
