# LSe 314 bench

A browser bench for the LSe 314 light sequencer. It models the light path the
instrument actually runs - a beam over the LDR panel, the conditioning chain,
the sequencer modes - and plays the instrument's own DSP under it.

Open `index.html` from any static server. It needs no build step and no network.

```
python3 -m http.server 8090        # then open /webapp/
```

## The tone is not a model

Nothing in the page synthesises anything. Each generator plays an mp3 in `snd/`
that is a headless render of the corresponding abstraction in
`software/pure data/rpi4_blockas_OS/lse314/01_AUDIO/`, produced by
`engine/mkall.py` with `pd -nogui -noaudio` and captured through `writesf~`.
Light drives the level - the sum of sensor output, the same quantity these
patches multiply their own signal by.

| page | abstraction | how it is instantiated here |
| --- | --- | --- |
| ADDITIVE | `1_SIN_4_ADD.pd` | `clone 1_SIN_4_ADD 32 24`, MUL_FACT 0.55 |
| THIRD-OCTAVE | `1_BP_FLT_FB_314.pd` | 32 bands over `SAMPLE/STRINGS/STR_SMPL0103.wav` |
| GRANULAR | `1_kac_grain.pd` | 32 instances, grain 90 ms, pitchshift -5 |
| LOOPER | `1_KAC_stretch.pd` | `MajStrecz` table, same sample |
| PING | `1_PING_314_CLONE_nodsp.pd` | 32 voices, captured off the `throw~ 1imp` bus |

## Re-rendering

```
cd engine
python3 mkall.py            # writes r_<name>.pd for every generator
./run.sh bp 12400           # render one, fast-forwarded
```

`mkall.py` creates `engine/lse`, a symlink to the patch tree, on first run: a Pd
message box cannot carry a path containing spaces and the tree lives under
`software/pure data/`.

Requires `pd` with `iemlib` and `cyclone` on the path. Renders land in
`engine/out/`; `sox` and `ffmpeg` do the normalise and the mp3 encode.

## Notes taken from the patches while building this

Three of these cost real time, so they are written down rather than rediscovered.

- **`1_PING_314_CLONE` vs `_nodsp`.** The plain abstraction carries a `switch~`
  that a `loadbang` sets to 0, so its DSP stays off until `sel 1` matches the
  sensor number. `main.pd` clones `_nodsp` for exactly this reason. A render
  harness that instantiates the plain one gets silence with no error.
- **The PING abstraction has no signal outlet.** Everything leaves through
  `throw~ 1imp`; outlet 0 is `outlet dspstatus`, a control outlet. The only
  capture is `catch~ 1imp`, of which `main.pd` holds exactly one.
- **PING's trigger inlet takes the sensor number, not a note.** The note arrives
  separately on `r 1_PING_SCALES` and is picked out by `route $1`. Because those
  two arrive on different paths, a strike can fire against the previous note's
  `bp~` centre - a known bug, on the author's own to-do list.
