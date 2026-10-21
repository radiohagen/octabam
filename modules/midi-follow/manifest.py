"""Follow source shares the pinned author checkout with Harmony."""
from pathlib import Path
import runpy
MODULE = runpy.run_path(str(Path(__file__).resolve().parent / '../midi-harmony/upstream/modules/midi-follow/manifest.py'))['MODULE']
