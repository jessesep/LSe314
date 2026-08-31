"""Render the REAL LSe 314 Pd generators headless, straight out of the
repo abstractions. Nothing here re-implements the DSP - every patch below
instantiates Kacper's own object and drives it the way the instrument does."""
import os, sys, math
from pdw import Patch

_ENG = os.path.dirname(os.path.abspath(__file__))
# A pd message box cannot carry a path containing spaces, and the patch tree
# lives under "software/pure data/". engine/lse is a symlink standing in for it;
# `python3 mkall.py` creates it on first run.
LSE = os.path.join(_ENG, "lse")
if not os.path.exists(LSE):
    os.symlink(os.path.join(os.path.dirname(os.path.dirname(_ENG)),
                            "software", "pure data", "rpi4_blockas_OS", "lse314"), LSE)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

STRINGS = os.path.join(LSE, "SAMPLE/STRINGS/STR_SMPL0103.wav")
DRUMS   = os.path.join(LSE, "SAMPLE/DRUM_LOOPS/DRL_SMPL0101.wav")

def light_field(t, n=32):
    """The light the panel actually reads: a slow beam over 32 LDRs."""
    out = []
    for i in range(n):
        col, row = i % 8, i // 8
        v = 0.5 + 0.5 * math.sin(t * 1.1 + col * 0.8 + row * 0.35)
        out.append(round(max(0.0, min(1.0, v * 0.85 + 0.12)), 4))
    return out

def transport(p, tr, wav, dur, chans=1):
    """open/start/stop a writesf~ and quit when the render is done."""
    w = p.obj("writesf~ %d" % chans)
    p.c(tr, 1, p.msgc(p, "open -bytes 2 %s" % wav, w), 0)
    d0 = p.obj("del 15"); p.c(tr, 0, d0, 0)
    m0 = p.msg("start"); p.c(d0, 0, m0, 0); p.c(m0, 0, w, 0)
    d1 = p.obj("del %d" % dur); p.c(tr, 0, d1, 0)
    m1 = p.msg("stop"); p.c(d1, 0, m1, 0); p.c(m1, 0, w, 0)
    d2 = p.obj("del %d" % (dur + 150)); p.c(tr, 0, d2, 0)
    mq = p.msg("; pd quit"); p.c(d2, 0, mq, 0)
    return w

def _msgc(p, text, target):
    m = p.msg(text); p.c(m, 0, target, 0); return m
Patch.msgc = staticmethod(lambda p, t, tgt: _msgc(p, t, tgt))

def send(p, tr, outlet, name, value):
    m = p.msg(str(value)); s = p.obj("s %s" % name)
    p.c(tr, outlet, m, 0); p.c(m, 0, s, 0)

# ---------------------------------------------------------------- ADDITIVE
def additive(mul, wav, dur=5200):
    """clone 1_SIN_4_ADD 32 24 - exactly as main.pd instantiates it."""
    p = Patch()
    lb = p.obj("loadbang"); tr = p.obj("t b b b b b")
    send(p, tr, 4, "MUL_FACT", mul)
    send(p, tr, 3, "RAMP_TIME", 0.30)
    send(p, tr, 2, "FUNDA_MENTAL", 0)
    cl = p.obj("clone 1_SIN_4_ADD 32 24")
    mix = p.obj("*~ 0.014")
    p.c(cl, 1, mix, 0)
    w = transport(p, tr, wav, dur)
    p.c(mix, 0, w, 0)
    # the light field, restated every 120 ms. The patch squares each reading
    # against the PREVIOUS one (moses -> * fans hot-inlet-first), so a value
    # only opens its voice on the second statement - which is what a live
    # sensor stream gives it.
    step = 0
    t = 0.0
    while step * 120 < dur:
        d = p.obj("del %d" % (step * 120)); p.c(tr, 0, d, 0)
        vals = light_field(t)
        # one message box per frame, listing every voice
        for i, v in enumerate(vals):
            if i % 4: continue          # 8 voices per frame, round-robin
            m = p.msg("%d %g" % ((i + step) % 32, vals[(i + step) % 32]))
            p.c(d, 0, m, 0); p.c(m, 0, cl, 0)
        step += 1; t += 0.12
    p.c(lb, 0, tr, 0)
    return p

# ------------------------------------------------------------ THIRD-OCTAVE
def thirdoctave(wav, dur=12000):
    """1_BP_FLT_FB_314 x 32 over a real string sample. Instantiated one by one
    rather than through [clone]: this abstraction's inlet 0 is the SIGNAL inlet,
    so clone's "<instance> <msg>" routing cannot reach the light inlet at all."""
    p = Patch()
    lb = p.obj("loadbang"); tr = p.obj("t b b b b b")
    send(p, tr, 4, "q_factor", 0.34)
    send(p, tr, 3, "inverse_q_mapping", 0)
    rd = p.obj("readsf~ 1")
    mo = p.msg("open %s" % STRINGS); p.c(tr, 2, mo, 0); p.c(mo, 0, rd, 0)
    dstart = p.obj("del 5"); p.c(tr, 0, dstart, 0)
    ms = p.msg("1"); p.c(dstart, 0, ms, 0); p.c(ms, 0, rd, 0)
    reopen = p.obj("t b b"); p.c(rd, 1, reopen, 0)
    p.c(reopen, 1, mo, 0); p.c(reopen, 0, ms, 0)

    voices = []
    for i in range(32):
        v = p.obj("1_BP_FLT_FB_314 %d 24" % i)
        p.c(rd, 0, v, 0)
        voices.append(v)
    acc = voices[0]
    for v in voices[1:]:
        a = p.obj("+~"); p.c(acc, 0, a, 0); p.c(v, 0, a, 1); acc = a
    mix = p.obj("*~ 0.02"); p.c(acc, 0, mix, 0)
    w = transport(p, tr, wav, dur)
    p.c(mix, 0, w, 0)

    step = 0; t = 0.0
    while step * 130 < dur:
        d = p.obj("del %d" % (step * 130)); p.c(tr, 0, d, 0)
        vals = light_field(t)
        for k in range(8):
            i = (k * 4 + step) % 32
            m = p.msg("%g" % max(0.3, vals[i]))
            p.c(d, 0, m, 0); p.c(m, 0, voices[i], 1)
        step += 1; t += 0.13
    p.c(lb, 0, tr, 0)
    return p

# ---------------------------------------------------------------- GRANULAR
def granular(wav, dur=12000):
    """1_kac_grain.pd - vanilla granulator, driven by its own receives."""
    p = Patch()
    lb = p.obj("loadbang"); tr = p.obj("t b b b b b b")
    tb1 = p.obj("table kacsound 220500")
    tb2 = p.obj("table mywindow 512")
    sf  = p.obj("soundfiler")
    mrd = p.msg("read -resize %s kacsound" % STRINGS)
    p.c(tr, 5, mrd, 0); p.c(mrd, 0, sf, 0)
    # hann window into mywindow, the shape the patch expects
    win = p.obj("until"); cnt = p.obj("f"); inc = p.obj("+ 1")
    mw  = p.msg("512"); p.c(tr, 4, mw, 0); p.c(mw, 0, win, 0)
    p.c(win, 0, cnt, 0); p.c(cnt, 0, inc, 0); p.c(inc, 0, cnt, 1)
    ex  = p.obj("expr 0.5 - 0.5*cos(6.2831853*$f1/512)")
    pk  = p.obj("pack 0 0"); tw = p.obj("tabwrite mywindow")
    p.c(cnt, 0, pk, 1); p.c(cnt, 0, ex, 0); p.c(ex, 0, pk, 0); p.c(pk, 0, tw, 0)
    send(p, tr, 3, "samplelength", 2.0)
    send(p, tr, 2, "graintimems", 90)
    g2 = p.obj("t b b b b"); p.c(tr, 1, g2, 0)
    send(p, g2, 3, "pitchshiftfactor", -5)
    send(p, g2, 2, "maxrandomdelay", 40)
    send(p, g2, 1, "maxrandomdelaypointer", 0.08)
    send(p, g2, 0, "go", 1)
    grains = [p.obj("1_kac_grain") for _ in range(32)]
    acc = grains[0]
    for g in grains[1:]:
        a = p.obj("+~"); p.c(acc, 0, a, 0); p.c(g, 0, a, 1); acc = a
    mix = p.obj("*~ 0.12"); p.c(acc, 0, mix, 0)
    w = transport(p, tr, wav, dur)
    p.c(mix, 0, w, 0)
    step = 0; t = 0.0
    while step * 130 < dur:
        d = p.obj("del %d" % (step * 130)); p.c(tr, 0, d, 0)
        pos = round(0.05 + 0.9 * (0.5 + 0.5 * math.sin(t * 0.42)), 4)
        m = p.msg(str(pos)); s = p.obj("s positioninfilerelative")
        p.c(d, 0, m, 0); p.c(m, 0, s, 0)
        m2 = p.msg("1"); s2 = p.obj("s play_1_grain")
        p.c(d, 0, m2, 0); p.c(m2, 0, s2, 0)
        step += 1; t += 0.13
    p.c(lb, 0, tr, 0)
    return p

# ------------------------------------------------------------------ LOOPER
def looper(wav, dur=12000):
    """1_KAC_stretch MajStrecz - the time-stretch looper on a real sample."""
    p = Patch()
    lb = p.obj("loadbang"); tr = p.obj("t b b b b")
    tb = p.obj("table MajStrecz 220500")
    sf = p.obj("soundfiler")
    mrd = p.msg("read -resize %s MajStrecz" % STRINGS)
    p.c(tr, 3, mrd, 0); p.c(mrd, 0, sf, 0)
    st = p.obj("1_KAC_stretch MajStrecz")
    mix = p.obj("*~ 0.7"); p.c(st, 0, mix, 0)
    w = transport(p, tr, wav, dur)
    p.c(mix, 0, w, 0)
    step = 0; t = 0.0
    while step * 250 < dur:
        d = p.obj("del %d" % (step * 250)); p.c(tr, 0, d, 0)
        v = round(0.25 + 1.6 * (0.5 + 0.5 * math.sin(t * 0.3)), 4)
        m = p.msg(str(v)); p.c(d, 0, m, 0); p.c(m, 0, st, 0)
        step += 1; t += 0.25
    p.c(lb, 0, tr, 0)
    return p

# -------------------------------------------------------------------- PING
def ping(wav, dur=9000):
    """1_PING_314_CLONE_nodsp x 32 - the variant main.pd actually clones
    (`clone 1_PING_314_CLONE_nodsp 32 64 100 100`). Three things this fixes:

    - the abstraction has NO signal outlet. Every voice leaves through
      `throw~ 1imp`, a global bus, so the only correct capture is `catch~ 1imp`
      (main.pd holds exactly one, at 204 457). Summing the voices' outlet 0 was
      summing `outlet dspstatus`, a control outlet.
    - the trigger inlet takes the SENSOR NUMBER, not a MIDI note. The note
      arrives separately on `r 1_PING_SCALES` and is picked out by `route $1`.
    - the plain `1_PING_314_CLONE` carries a `switch~` that a loadbang sets to 0,
      so its DSP is off until `sel 1` matches. `_nodsp` is the same patch with
      that switch removed, which is why the instrument uses it.
    """
    p = Patch()
    lb = p.obj("loadbang"); tr = p.obj("t b b b b b b b")
    tb = p.obj("table impulse 16")
    mi = p.msg("; impulse 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
    p.c(tr, 6, mi, 0)
    send(p, tr, 5, "Q_F", 0.55)
    send(p, tr, 4, "G_F", 0.6)
    send(p, tr, 3, "PTCH5_PAR_A1", 0.4)
    SCALE = [0, 3, 5, 7, 10, 12, 15, 17, 19, 22, 24, 27]
    def note_for(i):
        return 40 + SCALE[i % len(SCALE)] + 12 * (i // 12)
    voices = []
    for i in range(32):
        voices.append(p.obj("1_PING_314_CLONE_nodsp %d 64 100 100" % i))
        m = p.msg("%d %d" % (i, note_for(i)))
        s = p.obj("s 1_PING_SCALES")
        p.c(tr, 2, m, 0); p.c(m, 0, s, 0)
    bus = p.obj("catch~ 1imp")
    mix = p.obj("*~ 0.30"); p.c(bus, 0, mix, 0)
    w = transport(p, tr, wav, dur)
    p.c(mix, 0, w, 0)
    step = 0
    while 400 + step * 260 < dur:
        d = p.obj("del %d" % (400 + step * 260)); p.c(tr, 0, d, 0)
        i = (step * 7) % 32
        m = p.msg("%d" % i); p.c(d, 0, m, 0); p.c(m, 0, voices[i], 0)
        step += 1
    p.c(lb, 0, tr, 0)
    return p

JOBS = []
for mul in (0.15, 0.35, 0.55, 0.75, 0.95):
    JOBS.append(("add_%02d" % int(mul * 100), 5600,
                 lambda m=mul, : additive(m, os.path.join(OUT, "add_%02d.wav" % int(m * 100)))))
JOBS.append(("bp",    12400, lambda: thirdoctave(os.path.join(OUT, "bp.wav"))))
JOBS.append(("grain", 12400, lambda: granular(os.path.join(OUT, "grain.wav"))))
JOBS.append(("loop",  12400, lambda: looper(os.path.join(OUT, "loop.wav"))))
JOBS.append(("ping",   9400, lambda: ping(os.path.join(OUT, "ping.wav"))))

if __name__ == "__main__":
    want = sys.argv[1] if len(sys.argv) > 1 else None
    for name, ff, build in JOBS:
        if want and want != name: continue
        pt = build()
        pt.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r_%s.pd" % name))
        print("%s %d" % (name, ff))
