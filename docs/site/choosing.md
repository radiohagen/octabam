# Choose a Remix

A **module** adds one feature. A **remix** combines modules into an operating
system image. The three official remixes share the core features and differ
mainly in their effects.

## Keep the Stock Effects

Choose [Octabam Core](remix-core.md) for Kits, BRAIN, expanded scenes and
parameter locks, USB, and workflow fixes. All 14 stock effects remain in
the stock menus, with the LO-FI AMF control fixed.

## Add Effects to Individual Tracks

Choose [Octabam Inserts](remix-inserts.md) for SPECTRUM, CHARACTER,
MODULATION, TRANSIENT, and EUCLID on FX1 and FX2, plus GATE VERB and LOFI2
on FX2. The stock DELAY remains. These effects process their own tracks;
you do not need shared bus routing.

## Share a Delay and Reverb Bus

Choose [Octabam Bus](remix-bus.md) to send several tracks to the same delay
and reverb. Track 1 hosts the delay and track 5 hosts the reverb. Tracks
2–4 and 6–7 have SEND controls; track 8 retains the stock DELAY.
SPECTRUM, CHARACTER, and MODULATION are available on FX1.

The tested bus setup uses THRU machines on tracks 1 and 5 with no trigs of
their own. Read the [bus setup instructions](remix-bus.md) before choosing
this remix for an existing project.

## At a Glance

| Remix | Effects arrangement | DSP load display |
|---|---|---|
| **core** | Stock effects | Unavailable |
| **inserts** | Effects on individual tracks | Included |
| **bus** | Shared delay and reverb, plus FX1 inserts | Included |

All three reserve memory for the added features, leaving 12,895 sample and
recorder pages compared with 14,602 in stock OS. Core has no room for the
DSP portion of LOAD METER.

Test history belongs to a particular image and setup. Read the status on
each remix page; a module tested on hardware does not establish that the
whole remix has been tested.

Continue to [Build and install](build-flash.md), or
[create your own remix](own-remix.md) from the available modules.

For the radiohagen experimental MIDI integration, see [MIDI modules](midi-modules.md).
