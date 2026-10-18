"""sos-capture -- the recorder loop fix with a digital test signal in and the track outputs out over USB.

RECORDER LOOP FIX on usb-io-tracks-ab: the host plays a signal into inputs
A/B (USB INPUTS AB) and records the sixteen track channels (USB LAYOUT
TRACKS), so a sound-on-sound loop is captured sample-exact on the unit and
compared with the same input under the port
(`tools/hw/sos_capture.py`).
"""

from remix.schema import Proof, Remix

REMIX = Remix(
    name="sos-capture",
    family="mods", proof=Proof.PORT, proof_note="`make check` under the port; not on hardware in this form",
    doc="recorder fixes + USB (TRACKS out, AB in) (stock effects minus SPATIALIZER).",
    modules=("RECORDER LOOP FIX",
             "USB",
             "FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS",
             "COMB FILTER", "COMPRESSOR", "LO-FI", "DELAY",
             "PLATE REV", "SPRING REV", "DARK REV"),
    fx1=("FILTER", "EQUALIZER", "DJ EQ", "PHASER", "FLANGER", "CHORUS",
         "COMB FILTER", "COMPRESSOR", "LO-FI"),
    fallback="NONE",
    settings={("octabam.usb", "LAYOUT"): "TRACKS", ("octabam.usb", "INPUTS"): "AB"},
)
