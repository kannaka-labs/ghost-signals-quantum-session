"""Turn the session's quantum material into a whole song.

Quantum sources (all recorded in the song's provenance):
  - lead takes A/B/C: qrc-midi-v1 (A trained on the certified-random seed motif, B/C fanned out from
    the same trained reservoir with seeds read from the certified bytes);
  - ghost voice: blur-midi-v1 of take A;
  - groove: graph-v1, a 16-qubit graph state (one qubit per sixteenth step, downbeats biased toward
    |1>, neighbours anti-correlated); its most frequent bitstrings become bar-by-bar kick/hat patterns;
  - echo: retrocausal-echo-v1 on the melodic stem (lead + ghost).
Local (this file): chords, bass, pad, drum synthesis, arrangement, mixing. Nothing here is random:
every choice is either fixed by hand (harmony, form) or read from a quantum job's output.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from .music import notes_of

SR = 44100
BPM = 84
BEAT = 60 / BPM
STEP = BEAT / 4
BAR = 4 * BEAT

# D dorian, four-bar cycle: Dm7 | Cmaj7 | G7 | Dm7 (all tones inside the mode; G major is dorian's colour)
CHORDS = [
    {"root": 38, "pad": [50, 53, 57, 60]},
    {"root": 36, "pad": [48, 52, 55, 59]},
    {"root": 43, "pad": [50, 53, 55, 59]},
    {"root": 38, "pad": [50, 53, 57, 62]},
]

# Syncopated slots a kick may take when its qubit reads 1 (the downbeat always has one). The graph state
# is anti-correlated step to step, so raw bitstrings alternate; mapping them onto these slots turns that
# alternation into distinct, bar-by-bar kick placements instead of a wall of eighth notes.
KICK_SLOTS = (3, 6, 10, 11, 14)

# form: bars, and what plays. drums: none | hats | kickhat | full
SECTIONS = [
    {"name": "intro", "bars": 8, "pad": 0.55, "pad_lp": 650, "ghost": 0.8, "lead": None, "bass": 0.0, "drums": "none"},
    {"name": "verse", "bars": 16, "pad": 0.35, "pad_lp": 2600, "ghost": 0.35, "lead": "A", "bass": 0.8, "drums": "kickhat"},
    {"name": "lift", "bars": 16, "pad": 0.45, "pad_lp": 4200, "ghost": 0.45, "lead": "B", "bass": 1.0, "drums": "full"},
    {"name": "breakdown", "bars": 8, "pad": 0.4, "pad_lp": 1400, "ghost": 0.7, "lead": "C", "bass": 0.0, "drums": "hats"},
    {"name": "return", "bars": 16, "pad": 0.45, "pad_lp": 4200, "ghost": 0.55, "lead": "A", "bass": 1.0, "drums": "full"},
    {"name": "outro", "bars": 8, "pad": 0.5, "pad_lp": 700, "ghost": 0.8, "lead": None, "bass": 0.0, "drums": "hats"},
]


def mtof(p: float) -> float:
    return 440.0 * 2 ** ((p - 69) / 12)


def env_adsr(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    hold = max(n - a_n - d_n, 0)
    e = np.concatenate([np.linspace(0, 1, a_n, endpoint=False), np.linspace(1, s, d_n, endpoint=False),
                        np.full(hold, s), np.linspace(s, 0, r_n)])
    return e


def harmonics(freq: float, n: int, amps: list[float], detune: float = 0.0) -> np.ndarray:
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        if freq * k < SR / 2.2:
            out += a * np.sin(2 * np.pi * freq * k * (1 + detune) * t)
    return out


def lowpass(x: np.ndarray, fc: float, order: int = 4) -> np.ndarray:
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(x.shape[0], 1 / SR)
    h = 1 / np.sqrt(1 + (f / fc) ** (2 * order))
    return np.fft.irfft(X * (h[:, None] if x.ndim == 2 else h), n=x.shape[0], axis=0)


def highpass(x: np.ndarray, fc: float) -> np.ndarray:
    return x - lowpass(x, fc, order=2)


def add(buf: np.ndarray, sig: np.ndarray, at: float, pan: float = 0.0, gain: float = 1.0):
    """Mix a mono signal into a stereo buffer at time `at` with constant-power pan."""
    i = int(at * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    th = (pan + 1) * np.pi / 4
    buf[i:i + len(sig), 0] += gain * np.cos(th) * sig
    buf[i:i + len(sig), 1] += gain * np.sin(th) * sig


# ---- instruments --------------------------------------------------------------------------------

def lead_note(p, dur, vel):
    n = int((dur + 0.35) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.4, 0, 1)
    ph = 2 * np.pi * np.cumsum(mtof(p) * vib) / SR
    w = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.22 * np.sin(3 * ph) + 0.12 * np.sin(4 * ph) + 0.07 * np.sin(5 * ph)
    return w * env_adsr(n, 0.012, 0.25, 0.55, 0.3)[:n] * (vel / 127)


def ghost_note(p, dur, vel):
    n = int((dur + 0.8) * SR)
    w = harmonics(mtof(p), n, [1.0, 0.12])
    return w * env_adsr(n, 0.08, 0.4, 0.6, 0.8)[:n] * (vel / 127)


def pad_chord(pitches, dur):
    n = int((dur + 1.2) * SR)
    left = sum(harmonics(mtof(p), n, [1 / k for k in range(1, 9)], detune=-0.003) for p in pitches)
    right = sum(harmonics(mtof(p), n, [1 / k for k in range(1, 9)], detune=+0.003) for p in pitches)
    e = env_adsr(n, 0.6, 0.5, 0.8, 1.2)[:n]
    return np.stack([left * e, right * e], axis=1) / len(pitches)


def bass_note(p, dur):
    n = int((dur + 0.05) * SR)
    f = mtof(p)
    w = harmonics(f, n, [1.0, 0.5, 0.3, 0.18, 0.1]) + 0.8 * harmonics(f / 2, n, [1.0])
    return w * env_adsr(n, 0.005, 0.18, 0.7, 0.06)[:n]


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 70 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) + 0.3 * np.exp(-t / 0.003) * np.sin(2 * np.pi * 900 * t)


def snare(rng):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 1200)
    return 0.7 * noise * np.exp(-t / 0.11) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.07)


def hat(rng, open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 7000) * np.exp(-t / (0.09 if open_ else 0.018))


def reverb_ir(seconds=2.4, seed=7):
    rng = np.random.default_rng(seed)   # fixed seed: the room is part of the mix, not a creative choice
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / 0.55)[:, None]
    return lowpass(ir, 5000) * 0.03


def convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    y = np.fft.irfft(np.fft.rfft(x, n, axis=0) * np.fft.rfft(ir, n, axis=0), n, axis=0)
    return y[: len(x)]


# ---- grooves from the graph state ----------------------------------------------------------------

def groove_patterns(graph_output: dict, count: int = 4) -> list[str]:
    """Most frequent sampled bitstrings (qubit 0 = first sixteenth), as the bar patterns."""
    meas = graph_output["measurements"]
    rows = meas if isinstance(meas, list) else (meas.get("top") or meas.get("counts") or [])
    bits = []
    for r in rows:
        b = r.get("bitstring") or r.get("state") or r.get("outcome")
        if b and set(b) <= {"0", "1"}:
            bits.append(b)
    if not bits:
        raise ValueError(f"no bitstrings in graph output: {list(meas)}")
    return bits[:count]


# ---- arrangement ---------------------------------------------------------------------------------

def loop_notes(notes, start, bars):
    """Repeat a MIDI take's notes from `start` for `bars`, snapping the loop length up to whole bars."""
    if not notes:
        return []
    span = max(e for _, e, _, _ in notes)
    loop = max(1, int(np.ceil(span / BAR))) * BAR
    out, off = [], 0.0
    while off < bars * BAR:
        for s, e, p, v in notes:
            if off + s < bars * BAR:
                out.append((start + off + s, min(e - s, bars * BAR - off - s), p, v))
        off += loop
    return out


def build(takes: dict[str, str | Path], ghost_midi: str | Path, patterns: list[str]):
    """Render the song. Returns (stems dict of stereo arrays, melodic mono stem, section map)."""
    total_bars = sum(s["bars"] for s in SECTIONS)
    n = int((total_bars * BAR + 4) * SR)
    stems = {k: np.zeros((n, 2)) for k in ("drums", "bass", "pad")}
    melodic = np.zeros((n, 2))
    rng = np.random.default_rng(1)        # drum-noise texture only (fixed): no creative choice rides on it
    notes = {k: notes_of(v) for k, v in takes.items()}
    ghost = notes_of(ghost_midi)
    kicks, smap, t0 = [], [], 0.0
    K, SN, HC, HO = kick(), snare(rng), hat(rng), hat(rng, True)
    for sec in SECTIONS:
        smap.append({"name": sec["name"], "start_s": round(t0, 3), "bars": sec["bars"], "lead": sec["lead"],
                     "drums": sec["drums"]})
        for b in range(sec["bars"]):
            bt = t0 + b * BAR
            ch = CHORDS[b % 4]
            # pad, filtered per section
            pc = pad_chord([q + 12 for q in ch["pad"]], BAR)
            buf = np.zeros((int((BAR + 1.3) * SR), 2))
            buf[: len(pc)] += pc
            add_stereo(stems["pad"], highpass(lowpass(buf, sec["pad_lp"]), 250), bt, sec["pad"])
            pat = patterns[b % len(patterns)]
            hits = [i for i, c in enumerate(pat[:16]) if c == "1"]
            # drums
            if sec["drums"] != "none":
                for st in range(0, 16, 2):
                    open_ = st == 14 and st + 1 in hits
                    add(stems["drums"], HO if open_ else HC, bt + st * STEP, pan=0.25, gain=0.36 + 0.14 * (st in hits))
                for st in hits:
                    if st % 2:
                        add(stems["drums"], HC, bt + st * STEP, pan=-0.25, gain=0.14)
            if sec["drums"] in ("kickhat", "full"):
                ks = sorted({0} | {st for st in hits if st in KICK_SLOTS})
                for st in ks:
                    add(stems["drums"], K, bt + st * STEP, gain=0.95)
                    kicks.append(bt + st * STEP)
                # bass locks to the kick, root with a fifth pickup on the last sixteenth hit
                if sec["bass"]:
                    marks = ks + [16]
                    for a, z in zip(marks, marks[1:]):
                        add(stems["bass"], bass_note(ch["root"], (z - a) * STEP * 0.9), bt + a * STEP, gain=0.55 * sec["bass"])
                    if 15 in hits:
                        add(stems["bass"], bass_note(ch["root"] + 7, STEP * 0.8), bt + 15 * STEP, gain=0.45 * sec["bass"])
            if sec["drums"] == "full":
                for st in (4, 12):
                    add(stems["drums"], SN, bt + st * STEP, gain=0.6)
                if 7 in hits:
                    add(stems["drums"], SN, bt + 7 * STEP, gain=0.18)
        # melodic stem: lead take + ghost, both looped over the section
        if sec["lead"]:
            for s, d, p, v in loop_notes(notes[sec["lead"]], t0, sec["bars"]):
                add(melodic, lead_note(p + 12 * (p < 62), d, v), s, pan=-0.12, gain=0.32)
        for s, d, p, v in loop_notes(ghost, t0, sec["bars"]):
            add(melodic, ghost_note(p, d, v), s, pan=0.3 * np.sin(s), gain=0.11 * sec["ghost"])
        t0 += sec["bars"] * BAR
    # sidechain: pad and bass duck under the kick
    duck = np.ones(n)
    k_env = 1 - 0.45 * np.exp(-np.arange(int(0.3 * SR)) / SR / 0.09)
    for kt in kicks:
        i = int(kt * SR)
        seg = duck[i:i + len(k_env)]
        np.minimum(seg, k_env[: len(seg)], out=seg)
    stems["pad"] *= duck[:, None]
    stems["bass"] *= (0.5 + 0.5 * duck)[:, None]
    return stems, melodic, smap


def add_stereo(buf, sig, at, gain):
    i = int(at * SR)
    sig = sig[: max(len(buf) - i, 0)]
    buf[i:i + len(sig)] += gain * sig


def master(parts: list[np.ndarray], fade_s: float = 6.0) -> np.ndarray:
    n = max(len(p) for p in parts)
    mix = np.zeros((n, 2))
    for p in parts:
        mix[: len(p)] += p
    mix = highpass(mix, 28)
    # presence shelf: +4 dB above ~3 kHz (the synth voices are fundamental-heavy)
    X = np.fft.rfft(mix, axis=0)
    f = np.fft.rfftfreq(len(mix), 1 / SR)
    mix = np.fft.irfft(X * (1 + 0.58 / (1 + (3000 / np.maximum(f, 1)) ** 2))[:, None], n=len(mix), axis=0)
    mix = np.tanh(1.2 * mix / (np.abs(mix).max() + 1e-9)) / np.tanh(1.2)
    f = int(fade_s * SR)
    mix[-f:] *= np.linspace(1, 0, f)[:, None] ** 2
    return mix / (np.abs(mix).max() + 1e-9) * 0.89


def write_wav(path: str | Path, x: np.ndarray):
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def read_wav(path: str | Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        ch, sr, data = w.getnchannels(), w.getframerate(), w.readframes(w.getnframes())
    if sr != SR:
        raise ValueError(f"{path}: {sr} Hz, expected {SR}")
    x = np.frombuffer(data, "<i2").astype(float) / 32767
    return x.reshape(-1, ch) if ch > 1 else np.stack([x, x], axis=1)
