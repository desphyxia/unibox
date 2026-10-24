"""Stand-in sound effects for the playable prototype, synthesised from code (no recordings): creature chirps, egg knocks
and cracks, a hatch chime, pick-up and drop pops, munching, a sigh, sparkles, water (splash, slurp, bloop), a yawn and soft rain,
and the collie's own voice (collie_*: a soft "wuf", yips, a happy pant, a sigh, a squeaky yawn). Soft and short, for small ears.
Usage: python sfx.py OUT_DIR"""
import os, sys, wave
import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else "sfx"
os.makedirs(OUT, exist_ok=True)
SR = 44100
rng = np.random.default_rng(5)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.01, r=0.1, shape=2.0):
    """attack then a smooth decay to zero"""
    x = np.arange(n) / SR
    e = np.minimum(x / max(a, 1e-4), 1.0)
    tail = np.clip((x[-1] - x) / max(r, 1e-4), 0, 1) ** shape
    return e * np.minimum(1.0, tail * 1.0 + (x < x[-1] - r))


def glide(f0, f1, d, harm=(1.0, 0.3, 0.1), vib=0.0, vib_rate=7.0):
    x = t(d)
    f = f0 * (f1 / f0) ** (x / d)
    f = f * (1 + vib * np.sin(2 * np.pi * vib_rate * x))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return sum(a * np.sin(ph * (k + 1)) for k, a in enumerate(harm))


def bell(f, d, decay=6.0):
    x = t(d)
    return (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 4) + 0.2 * np.sin(2 * np.pi * f * 5.4 * x) * np.exp(-x * 9)) * np.exp(-x * decay)


def noise(d):
    return rng.standard_normal(int(SR * d))


def lowpass(x, k):
    """simple one-pole smoothing; k in (0,1), smaller is darker"""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += k * (v - acc)
        y[i] = acc
    return y


def mix(*parts):
    """parts: (start_seconds, signal)"""
    n = max(int(s * SR) + len(p) for s, p in parts)
    out = np.zeros(n)
    for s, p in parts:
        i = int(s * SR)
        out[i:i + len(p)] += p
    return out


def save(name, x, gain=0.5):
    x = x / (np.max(np.abs(x)) + 1e-9) * gain
    fade = min(len(x), int(SR * 0.01))
    x[-fade:] *= np.linspace(1, 0, fade)
    pcm = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", name, f"{len(x) / SR:.2f}s")


def chirp(f0, f1, d):
    s = glide(f0, f1, d, (1.0, 0.35, 0.12), vib=0.02)
    return s * env(len(s), 0.012, d * 0.8, 1.5)


# the creature: a soft two-part chirp, a happy trill, a sigh, a yawn
save("chirp", mix((0, chirp(820, 1250, 0.09)), (0.11, chirp(900, 1500, 0.12))), 0.45)
save("chirp2", mix((0, chirp(1000, 1400, 0.08)), (0.09, chirp(1100, 1650, 0.08)), (0.18, chirp(1250, 1800, 0.11))), 0.45)
save("happy", mix(*[(0.085 * i, chirp(f, f * 1.25, 0.1)) for i, f in enumerate((880, 1100, 1320, 1650))]), 0.45)
sig = lowpass(noise(0.9), 0.12) * env(int(SR * 0.9), 0.15, 0.6, 1.2) * 0.6 + glide(420, 300, 0.9, (1.0, 0.2)) * env(int(SR * 0.9), 0.1, 0.7, 1.4) * 0.5
save("sigh", sig, 0.32)
# the egg: a soft wooden knock, cracks, the hatch
knock = mix((0, glide(380, 300, 0.16, (1.0, 0.25)) * env(int(SR * 0.16), 0.002, 0.15, 3)), (0, lowpass(noise(0.03), 0.4) * env(int(SR * 0.03), 0.001, 0.03, 2) * 0.6))
save("knock", knock, 0.5)
crack = mix(*[(rng.uniform(0, 0.12), lowpass(noise(0.02), 0.7) * env(int(SR * 0.02), 0.001, 0.02, 2)) for _ in range(9)])
save("crack", crack, 0.4)
notes = (659, 784, 988, 1319, 1568)
save("hatch", mix(*[(0.09 * i, bell(f, 1.4, 3.0)) for i, f in enumerate(notes)], (0.0, lowpass(noise(0.5), 0.05) * env(int(SR * 0.5), 0.05, 0.45) * 0.4)), 0.42)
# handling things
save("pickup", glide(500, 900, 0.08, (1.0, 0.2)) * env(int(SR * 0.08), 0.004, 0.07, 2), 0.35)
save("drop", glide(600, 320, 0.1, (1.0, 0.2)) * env(int(SR * 0.1), 0.003, 0.09, 2), 0.35)
munch = mix(*[(0.13 * i, lowpass(noise(0.07), 0.35) * env(int(SR * 0.07), 0.004, 0.06, 2)) for i in range(3)])
save("munch", munch, 0.38)
save("sparkle", mix(*[(0.06 * i, bell(f, 0.6, 7.0)) for i, f in enumerate((1568, 2093, 2637))]), 0.3)
save("chime", mix((0, bell(784, 1.2, 3.5)), (0.12, bell(1175, 1.2, 3.5))), 0.38)
save("pop", glide(700, 1100, 0.06, (1.0, 0.1)) * env(int(SR * 0.06), 0.002, 0.05, 2), 0.3)

# water: a splash (a soft noisy burst with a few bubbles), a slurp for drinking, and a little bloop for a ripple
def bubble(f, d):
    s = glide(f, f * 1.8, d, (1.0, 0.15))
    return s * env(len(s), 0.004, d * 0.85, 2.0)


spl = lowpass(noise(0.45), 0.18) * env(int(SR * 0.45), 0.005, 0.4, 2.2)
save("splash", mix((0, spl), *[(0.05 + 0.06 * i + rng.uniform(0, 0.03), bubble(rng.uniform(500, 900), 0.06) * 0.5) for i in range(5)]), 0.4)
save("slurp", mix(*[(0.09 * i, bubble(f, 0.07)) for i, f in enumerate((380, 460, 420))], (0, lowpass(noise(0.3), 0.08) * env(int(SR * 0.3), 0.02, 0.25) * 0.4)), 0.34)
save("bloop", bubble(520, 0.12), 0.3)

# the evening: a sleepy yawn (a breath in rising, then a long sigh falling), and soft rain (a seamless 4 s loop)
yb = glide(300, 520, 0.55, (1.0, 0.25, 0.08)) * env(int(SR * 0.55), 0.18, 0.2, 1.2)
yf = glide(520, 260, 0.9, (1.0, 0.2)) * env(int(SR * 0.9), 0.05, 0.8, 1.3)
breath = lowpass(noise(1.45), 0.1) * env(int(SR * 1.45), 0.3, 0.9, 1.2) * 0.35
save("yawn", mix((0, yb * 0.6), (0.5, yf * 0.55), (0, breath)), 0.3)
L = 4.0
n = int(SR * L)
hiss = lowpass(noise(L + 0.5), 0.25)[:n] * 0.25
drops = np.zeros(n)
for _ in range(220):
    at = rng.integers(0, n - int(SR * 0.05))
    d = bubble(rng.uniform(1400, 3200), 0.03) * rng.uniform(0.15, 0.5)
    drops[at:at + len(d)] += d
rain = hiss + drops
fade = int(SR * 0.5)                                       # seamless: the end blends into the start
rain[:fade] = rain[:fade] * np.linspace(0, 1, fade) + rain[-fade:] * np.linspace(1, 0, fade)
rain = rain[:-fade]
x = rain / (np.max(np.abs(rain)) + 1e-9) * 0.28
with wave.open(os.path.join(OUT, "rain.wav"), "wb") as w:   # no fade at the end: it loops
    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
    w.writeframes((x * 32767).astype(np.int16).tobytes())
print("wrote rain", f"{len(x) / SR:.2f}s")


# ------------------------------------------------------------------ the collie's own voice (collie_*: the game plays a
# kind's own sound where it has one, else the shared one). A voice is a buzz (a tone with many harmonics) shaped by the
# mouth's resonances, plus breath; soft and short like the chirps: a gentle "wuf" when called, a little yip, happy yips
# with a pant, a dog's sigh through the nose, and a squeaky yawn.
drng = np.random.default_rng(36)                          # (its own seed, so the sounds above come out unchanged)


def track(points, d):
    """a value over time from (seconds, value) points"""
    x = t(d)
    p = np.array(points, float)
    return np.interp(x, p[:, 0], p[:, 1])


def resonate(x, f, bw):
    """a two-pole resonance at frequency f (a number or a track) with bandwidth bw, normalised to unit peak gain"""
    f = np.broadcast_to(np.asarray(f, float), x.shape)
    r = np.exp(-np.pi * bw / SR)
    a1 = 2 * r * np.cos(2 * np.pi * f / SR)
    a2 = -r * r
    g = 1 - r
    y = np.zeros_like(x)
    y1 = y2 = 0.0
    for i in range(len(x)):
        v = g * x[i] + a1[i] * y1 + a2 * y2
        y[i] = v
        y2, y1 = y1, v
    return y


def buzz(f0):
    """a voiced source following the pitch track f0: harmonics falling off softly, up to about 4 kHz"""
    ph = 2 * np.pi * np.cumsum(f0) / SR
    out = np.zeros_like(f0)
    for k in range(1, 24):
        out += np.where(f0 * k < 4000, np.sin(ph * k) / k ** 1.1, 0.0)
    return out


def vocal(d, f0, formants, breath=0.15, voiced=1.0):
    """d seconds of voice: f0 a pitch track, formants [(frequency or track, bandwidth, level)], breath the share of
    noise"""
    src = buzz(f0) * voiced + lowpass(drng.standard_normal(len(f0)), 0.5) * breath
    return sum(lvl * resonate(src, f, bw) for f, bw, lvl in formants)


def wuf(d=0.2, lift=1.0):
    """a soft, closed-mouth bark: a quick rise then a fall in pitch, round and low"""
    f0 = track([(0, 380 * lift), (0.03, 450 * lift), (d, 290 * lift)], d)
    v = vocal(d, f0, [(track([(0, 700), (d, 480)], d), 160, 1.0), (track([(0, 1200), (d, 900)], d), 220, 0.5),
                      (2500, 400, 0.12)], breath=0.25)
    return lowpass(v, 0.35) * env(len(v), 0.008, d * 0.85, 1.6)


def yip(d=0.085, f=800):
    """a little high yip: up and down"""
    f0 = track([(0, f * 0.9), (d * 0.35, f * 1.3), (d, f * 0.95)], d)
    v = vocal(d, f0, [(950, 180, 1.0), (1900, 260, 0.55), (3000, 400, 0.15)], breath=0.12)
    return lowpass(v, 0.5) * env(len(v), 0.005, d * 0.8, 1.6)


def pant(d=0.075):
    """one breath of a happy pant: a whispered "hah" """
    n = drng.standard_normal(int(SR * d))
    v = resonate(n, 950, 250) + 0.6 * resonate(n, 1600, 350) + 0.2 * resonate(n, 2600, 500)
    return v * env(len(v), 0.012, d * 0.7, 1.4)


save("collie_chirp", wuf(), 0.42)
save("collie_chirp2", mix((0, yip(0.085, 780)), (0.12, yip(0.09, 860))), 0.6)
save("collie_happy", mix((0, yip(0.08, 760)), (0.1, yip(0.08, 860)), (0.2, yip(0.09, 960)),
                         *[(0.42 + 0.15 * i, pant() * (0.55 - 0.08 * i)) for i in range(4)]), 0.6)
d = 0.85                                                  # a sigh: a tiny whimper, then a long breath out of the nose
whim = vocal(0.2, track([(0, 520), (0.2, 430)], 0.2), [(600, 150, 1.0), (1300, 250, 0.3)], breath=0.1)
whim = lowpass(whim, 0.3) * env(len(whim), 0.03, 0.15, 1.5)
nose = drng.standard_normal(int(SR * d))
nose = (resonate(nose, 450, 300) + 0.5 * resonate(nose, 1100, 500)) * env(int(SR * d), 0.08, 0.65, 1.3)
save("collie_sigh", mix((0, whim * 0.35), (0.1, lowpass(nose, 0.3))), 0.4)
d = 1.1                                                   # a yawn: a squeaky whine that opens up, then closes and falls
yv = vocal(d, track([(0, 520), (0.35, 820), (0.75, 560), (d, 380)], d),
           [(track([(0, 500), (0.35, 850), (0.9, 450)], d), 170, 1.0),
            (track([(0, 1200), (0.35, 1450), (0.9, 800)], d), 240, 0.45), (2700, 450, 0.1)], breath=0.3)
save("collie_yawn", lowpass(yv, 0.3) * env(len(yv), 0.12, 0.35, 1.3), 0.3)
