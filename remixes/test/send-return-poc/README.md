# POST FADER and T8 RETURNS integration

This test remix selects the current `octabam-bus` core plus POST FADER and
RETURNS. BusDelay still runs on T1 and BusVerb on T5, but their wet returns
are controlled on T8. T1/T5 remain usable source tracks. The stock T8 DELAY
selection is replaced by RETURNS. SEND uses the builder's normal internal
P placement because the expanded delay routing overlaps its old fixed
window address; all other selected window placements follow the base rig.

Track mute and LEVEL changes preserve original bus participation, so they
leave other tracks' send gains unchanged. The effect states continue to
run and the independent returns let existing tails survive a source-host
mute. Use `host-rig` with this remix to assign the selected bound IDs.

This is an opt-in integration fixture, derived from PR 542 and the
maintained local POST FADER prototype. Current emulator checks and physical
hardware acceptance must be reported separately; historical prototype
checks do not validate the updated implementation.

Focused gates:

```sh
.venv/bin/python3 tools/verify/verify_postfader_hook.py test/send-return-poc
.venv/bin/python3 tools/verify/verify_postfader.py test/send-return-poc --image out/mainos_bus.bin --project /path/to/template
.venv/bin/python3 tools/verify/verify_returns.py test/send-return-poc
```

The firmware gate stages owned copies and generated audio under `out/`.
It does not edit a mounted card or the supplied template.
