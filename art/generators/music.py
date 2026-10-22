"""Background music for the playable prototype, composed and played from code (no recordings, no samples): two
seamless loops in F major that the game crossfades with island time (docs/first-ten-minutes.md: "soft music"; no
narrator).
  day.wav    76 beats a minute: a warm pad, a soft bass, and a music-box tune over the chords, with a few high sparkles
  night.wav  60 beats a minute: the same chords as a lullaby, slower, lower and sparser
Each is 16 bars; the echo that rings past the end is folded back onto the start, so the loop has no seam.
Usage: python music.py OUT_DIR"""
import os, sys, wave
import numpy as np
from scipy.signal import lfilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "music"
os.makedirs(OUT, exist_ok=True)
SR = 44100

# F major; chords as note numbers (MIDI), one bar each, the 8-bar progression played twice
CHORDS = [
    [53, 57, 60, 64],   # Fmaj7
    [50, 53, 57, 60],   # Dm7
    [46, 50, 53, 57],   # Bbmaj7
    [48, 53, 55, 60],   # Csus4
    [53, 57, 60, 64],   # Fmaj7
    [45, 48, 52, 55],   # Am7
    [46, 50, 53, 57],   # Bbmaj7
    [48, 52, 55, 58],   # C7
]
PENTA = [0, 2, 4, 7, 9]                               # F G A C D, as steps from F


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def env_adsr(n, a, d, s, r):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0)
    e = np.where(t > a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)), e)
    rel = np.clip((t[-1] - t) / max(r, 1e-4), 0, 1)
    return e * rel


def tone(f, dur, partials, a=0.005, d=0.4, s=0.0, r=0.3, detune=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, (mult, amp, decay) in enumerate(partials):
        out += amp * np.sin(2 * np.pi * f * mult * (1 + detune) * t) * np.exp(-t * decay)
    return out * env_adsr(n, a, d, s, r)


def music_box(f, dur):
    return tone(f, dur, [(1.0, 1.0, 2.2), (2.0, 0.22, 5.0), (3.0, 0.08, 9.0), (5.4, 0.04, 14.0)], 0.002, 0.6, 0.0, 0.2)


def pad_voice(f, dur):
    p = [(1.0, 1.0, 0.0), (2.0, 0.18, 0.0), (3.0, 0.05, 0.0)]
    return (tone(f, dur, p, 0.9, 1.0, 0.85, 1.2, 0.0015) + tone(f, dur, p, 0.9, 1.0, 0.85, 1.2, -0.0015)) * 0.5


def bass(f, dur):
    return tone(f, dur, [(1.0, 1.0, 1.2), (2.0, 0.25, 3.0)], 0.01, 0.8, 0.25, 0.4)


def reverb(x, wet=0.28):
    """a small, soft room: four combs and two allpasses (Schroeder), darkened"""
    out = np.zeros_like(x)
    for dly, g in ((1557, 0.80), (1617, 0.79), (1491, 0.81), (1422, 0.80)):
        b = np.zeros(dly + 1); b[0] = 1.0
        a = np.zeros(dly + 1); a[0] = 1.0; a[dly] = -g
        out += lfilter(b, a, x)
    out /= 4
    for dly, g in ((225, 0.7), (556, 0.7)):
        b = np.zeros(dly + 1); b[0] = -g; b[dly] = 1.0
        a = np.zeros(dly + 1); a[0] = 1.0; a[dly] = -g
        out = lfilter(b, a, out)
    out = lfilter([0.25], [1, -0.75], out)                # darker
    return x * (1 - wet) + out * wet * 3.0


def place(buf, at, sig, gain=1.0):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain


def compose(name, bpm, mel_lo, density, seed, sparkle):
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bars = 16
    length = bars * 4 * beat
    tail = 6.0
    buf = np.zeros(int(SR * (length + tail)))
    # pad and bass
    for bar in range(bars):
        ch = CHORDS[bar % 8]
        t0 = bar * 4 * beat
        for m in ch:
            place(buf, t0, pad_voice(hz(m), 4 * beat + 1.2), 0.07)
        place(buf, t0, bass(hz(ch[0] - 12), 2 * beat), 0.22)
        place(buf, t0 + 2 * beat, bass(hz(ch[0] - 12 + (7 if bar % 2 else 0)), 2 * beat), 0.16)
    # the tune: an 8-bar phrase made once, played twice (the second time with a little variation)
    scale = [mel_lo + 12 * o + s for o in range(3) for s in PENTA]
    rhythms = [[0, 1, 2, 3], [0, 1.5, 2, 3], [0, 2, 2.5, 3], [0, 1, 3], [0, 2], [0, 0.5, 1, 2]]
    phrase = []
    idx = 5
    for bar in range(8):
        r = rhythms[rng.integers(0, len(rhythms))] if rng.random() < density else [0, 2]
        notes = []
        for k, at in enumerate(r):
            idx = int(np.clip(idx + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(scale) - 1))
            m = scale[idx]
            if at in (0, 2):                                  # strong beats: the nearest chord tone
                pcs = [c % 12 for c in CHORDS[bar]]
                cand = [x for x in scale if x % 12 in pcs]
                m = min(cand, key=lambda x: abs(x - m))
                idx = scale.index(m)
            notes.append((at, m))
        if bar in (3, 7):                                     # phrase ends: a long note on the root
            notes = [(0, notes[0][1]), (2, min([x for x in scale if x % 12 == CHORDS[bar][0] % 12], key=lambda x: abs(x - notes[0][1])))]
        phrase.append(notes)
    for rep in range(2):
        for bar, notes in enumerate(phrase):
            t0 = (rep * 8 + bar) * 4 * beat
            for k, (at, m) in enumerate(notes):
                if rep == 1 and k == len(notes) - 1 and bar not in (3, 7) and rng.random() < 0.5:
                    m = scale[min(len(scale) - 1, scale.index(m) + 1)]
                nxt = notes[k + 1][0] if k + 1 < len(notes) else 4
                place(buf, t0 + at * beat, music_box(hz(m), (nxt - at) * beat + 1.0), 0.32)
    # sparkles: a high bell now and then, off the beat
    for bar in range(bars):
        if rng.random() < sparkle:
            m = scale[-1] + 12 + rng.choice([0, 2, 4, 7])
            place(buf, bar * 4 * beat + rng.choice([1.5, 2.5, 3.5]) * beat, music_box(hz(m), 1.2), 0.1)
    y = reverb(buf)
    # fold what rings past the end back onto the start, so the loop is seamless
    n = int(SR * length)
    y[:len(y) - n] += y[n:]
    y = y[:n]
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.5
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    print("wrote", name, f"{n / SR:.1f}s")


compose("day", 76, 65, 0.85, 3, 0.45)       # the tune from F4 up
compose("night", 60, 53, 0.35, 8, 0.2)      # from F3, sparse
