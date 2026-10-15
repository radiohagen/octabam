"""The existing STEM REC PIO first-sector fix, without recording features."""
from remix.schema import Category, Detour, Gate, Kind, Linked, Module, Proof

MODULE = Module(
    name="pio-write-fix", key="PIO WRITE FIX", kind=Kind.CF_PATCH,
    category=Category.FIXES, author="yvesrosius; standalone packaging: mattiaswolff",
    author_url="https://github.com/yvesrosius",
    proof=Proof.CHECK, proof_note="Original STEM REC fix; standalone emulator qualification, no hardware claim",
    doc="Advance the PIO card writer's pointer and count before sending its first sector; prevents an interrupt from duplicating a sector or stalling.",
    requires=("MEMORY",),
    conflicts=(("STEM REC", "already owns this same PIO first-sector fix"),),
    linked=(Linked("pio_write", "modules/pio-write-fix/first.s", dram=True,
                   reference=(0x400d7000, "14b22d23ccd0a4a209ff69f20d3ed5c5d25e889f1d7ffed65c8d23f9a3c5051b")),),
    detours=(Detour(0x40014cfe, bytes.fromhex("207946c8c594"), "pio_write", "pio_write_first",
                    "same first-sector ordering as STEM REC; pointer and count advanced before data", kind="jmp"),),
    gates=(Gate("tools/verify/verify_pio_write.py", venv=True, stage="image"),),
)
