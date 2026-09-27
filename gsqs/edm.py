"""The third iteration: a 140 bpm half-time deep-bass arrangement of the quantum session, built for vocals.

Same quantum sources as gsqs/song.py (lead takes, ghost voice, graph-state groove), re-voiced:
sub + growl bass with a wobble whose rate each bar is read from that bar's graph-state bitstring,
supersaw chords and a pluck lead in the drops, half-time drums, risers, snare rolls and impacts.
Nothing in this file makes a creative choice from a pseudo-random source: noise textures use fixed
seeds, and every musical decision is either written here (form, harmony) or read from a quantum job.
"""
from __future__ import annotations

import numpy as np

from .music import notes_of
from .song import (SR, env_adsr, ghost_note, harmonics, highpass, lowpass, mtof, pad_chord)

BPM = 140
BEAT = 60 / BPM
STEP = BEAT / 4
BAR = 4 * BEAT
SOURCE_BEAT = 60 / 84            # the quantum MIDI takes were written at 84 bpm

CHORDS = [  # D dorian, four-bar cycle: Dm7 | Cmaj7 | G7 | Dm7
    {"root": 38, "pad": [62, 65, 69, 72]},
    {"root": 36, "pad": [60, 64, 67, 71]},
    {"root": 43, "pad": [62, 65, 67, 71]},
    {"root": 38, "pad": [62, 65, 69, 74]},
]
KICK_SLOTS = (3, 6, 10, 11, 14)

SECTIONS = [
    {"name": "intro", "bars": 8, "kind": "ambient"},
    {"name": "verse", "bars": 16, "kind": "verse", "lead": "A"},
    {"name": "build", "bars": 8, "kind": "build"},
    {"name": "drop", "bars": 16, "kind": "drop", "lead": "A"},
    {"name": "break", "bars": 16, "kind": "break", "lead": "C"},
    {"name": "build2", "bars": 8, "kind": "build"},
    {"name": "drop2", "bars": 16, "kind": "drop", "lead": "B"},
    {"name": "outro", "bars": 8, "kind": "ambient"},
]


def section_starts():
    t, out = 0.0, {}
    for s in SECTIONS:
        out[s["name"]] = t
        t += s["bars"] * BAR
    return out, t


# ---- voices -------------------------------------------------------------------------------------

def saw(freq, n, detune=0.0, parts=24):
    return harmonics(freq, n, [(-1) ** (k + 1) / k for k in range(1, parts + 1)], detune)


def supersaw(pitches, dur, voices=5, spread=0.012):
    n = int((dur + 0.3) * SR)
    L, R = np.zeros(n), np.zeros(n)
    for p in pitches:
        for v in range(voices):
            d = spread * (v - (voices - 1) / 2) / ((voices - 1) / 2)
            s = saw(mtof(p), n, detune=d, parts=16)
            L += s * (0.5 + 0.5 * (v % 2))
            R += s * (0.5 + 0.5 * ((v + 1) % 2))
    e = env_adsr(n, 0.01, 0.2, 0.75, 0.3)[:n]
    return np.stack([L * e, R * e], axis=1) / (len(pitches) * voices)


def pluck(p, dur, vel):
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    raw = saw(mtof(p), n, parts=18)
    bright = lowpass(raw, 5000) * np.exp(-t / 0.09)
    body = lowpass(raw, 1200)
    return (0.6 * bright + 0.5 * body) * env_adsr(n, 0.002, 0.18, 0.35, 0.25)[:n] * (vel / 127)


def sub_note(p, dur):
    n = int((dur + 0.03) * SR)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * mtof(p) * t)
    return np.tanh(1.6 * w) * env_adsr(n, 0.004, 0.05, 0.95, 0.03)[:n]


def growl(p, dur, rate_steps, phase0=0.0):
    """Saw + FM stack through a wobbling low-pass. The filter is interpolated between four statically
    filtered copies, so a time-varying cutoff costs four FFT filters instead of a per-sample loop."""
    n = int((dur + 0.02) * SR)
    t = np.arange(n) / SR
    f = mtof(p)
    mod = np.sin(2 * np.pi * f * 2 * t) * 2.2
    raw = saw(f, n, parts=30) + 0.6 * np.sin(2 * np.pi * f * t + mod)
    raw = np.tanh(1.8 * raw)
    bands = [lowpass(raw, fc) for fc in (180, 450, 1100, 2800)]
    lfo = 0.5 - 0.5 * np.cos(2 * np.pi * (t / (rate_steps * STEP) + phase0))   # 0..1
    x = lfo * 3
    i = np.clip(x.astype(int), 0, 2)
    frac = x - i
    stack = np.stack(bands)
    out = stack[i, np.arange(n)] * (1 - frac) + stack[i + 1, np.arange(n)] * frac
    return out * env_adsr(n, 0.005, 0.05, 0.9, 0.02)[:n]


def kick808():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 42 + 110 * np.exp(-t / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22)
    click = np.exp(-t / 0.002) * np.sin(2 * np.pi * 1800 * t) * 0.4
    return np.tanh(1.4 * (body + click))


def snare_big(rng):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 900) * np.exp(-t / 0.14)
    tone = (np.sin(2 * np.pi * 190 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t / 0.06)
    return np.tanh(1.3 * (0.65 * noise + 0.55 * tone))


def hat16(rng):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return lowpass(highpass(rng.standard_normal(n), 7000), 12000) * np.exp(-t / 0.012)


def riser(seconds, rng):
    n = int(seconds * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    bands = [highpass(lowpass(noise, fc), fc / 3) for fc in (600, 1800, 5000, 12000)]
    x = t * 3
    i = np.clip(x.astype(int), 0, 2)
    frac = x - i
    stack = np.stack(bands)
    sweep = stack[i, np.arange(n)] * (1 - frac) + stack[i + 1, np.arange(n)] * frac
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * t ** 2) / SR) * 0.25
    return (sweep * 0.5 + tone) * t ** 1.5


def impact(rng):
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.7)
    air = lowpass(rng.standard_normal(n), 3000) * np.exp(-t / 0.5) * 0.3
    return np.tanh(1.5 * (boom + air))


# ---- arrangement ---------------------------------------------------------------------------------

def put(buf, sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= len(buf) or i < 0:
        return
    if sig.ndim == 1:
        th = (pan + 1) * np.pi / 4
        sig = np.stack([np.cos(th) * sig, np.sin(th) * sig], axis=1)
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += gain * sig


def retime(notes, start, bars):
    """Map an 84-bpm take onto the 140-bpm grid by beats, looping to fill `bars`."""
    beats = [(s / SOURCE_BEAT, (e - s) / SOURCE_BEAT, p, v) for s, e, p, v in notes]
    if not beats:
        return []
    span = max(b + d for b, d, _, _ in beats)
    loop = max(1, int(np.ceil(span / 4))) * 4
    out, off = [], 0.0
    while off < bars * 4:
        for b, d, p, v in beats:
            if off + b < bars * 4:
                out.append((start + (off + b) * BEAT, min(d, bars * 4 - off - b) * BEAT, p, v))
        off += loop
    return out


def wobble_rate(pattern: str) -> int:
    """Wobble period in sixteenth steps, read from the bar's graph-state bitstring."""
    return (8, 4, 2, 4)[pattern[:16].count("1") % 4]


def build(takes, ghost_midi, patterns):
    starts, total = section_starts()
    n = int((total + 3) * SR)
    stems = {k: np.zeros((n, 2)) for k in ("drums", "bass", "music", "fx")}
    rng = np.random.default_rng(3)
    notes = {k: notes_of(v) for k, v in takes.items()}
    ghost = notes_of(ghost_midi)
    K, SN, HH, IMP = kick808(), snare_big(rng), hat16(rng), impact(rng)
    kicks = []
    for sec in SECTIONS:
        t0, kind = starts[sec["name"]], sec["kind"]
        for b in range(sec["bars"]):
            bt = t0 + b * BAR
            ch = CHORDS[b % 4]
            pat = patterns[b % len(patterns)]
            hits = [i for i, c in enumerate(pat[:16]) if c == "1"]
            # pads everywhere except the drops (supersaws take over there)
            if kind != "drop":
                put(stems["music"], highpass(lowpass(pad_chord(ch["pad"], BAR), 2200 if kind != "ambient" else 900), 200),
                    bt, gain=0.5 if kind in ("ambient", "break") else 0.35)
            if kind == "drop":
                put(stems["music"], highpass(supersaw(ch["pad"], BAR * 0.98), 220), bt, gain=0.55)
            # drums
            if kind in ("verse", "drop"):
                ks = sorted({0} | {s for s in hits if s in KICK_SLOTS and s != 8})
                for s in ks:
                    put(stems["drums"], K, bt + s * STEP, gain=1.0)
                    kicks.append(bt + s * STEP)
                if kind == "drop" or b % 2 == 1:
                    put(stems["drums"], SN, bt + 8 * STEP, gain=0.8)
                for s in range(16):
                    if kind == "drop" or s % 2 == 0:
                        put(stems["drums"], HH, bt + s * STEP, pan=0.3 * (1 if s % 4 else -1),
                            gain=0.09 + 0.09 * (s in hits))
                # sub bass locks to the kicks
                marks = ks + [16]
                for a, z in zip(marks, marks[1:]):
                    put(stems["bass"], sub_note(ch["root"] - 12, (z - a) * STEP * 0.95), bt + a * STEP,
                        gain=0.8 if kind == "drop" else 0.55)
                if kind == "drop":
                    rate = wobble_rate(pat)
                    put(stems["bass"], growl(ch["root"], BAR * 0.98, rate), bt, gain=0.33)
            if kind == "break" and b >= 8:
                for s in range(0, 16, 4):
                    put(stems["drums"], HH, bt + s * STEP, gain=0.12)
            if kind == "build":
                # snare roll: quarters, eighths, sixteenths, thirty-seconds across the 8 bars
                div = (4, 4, 2, 2, 1, 1, 0.5, 0.5)[b]
                s = 0.0
                while s < 16:
                    put(stems["drums"], SN, bt + s * STEP, gain=0.12 + 0.3 * (b / 7))
                    s += div
        if kind == "build":
            put(stems["fx"], lowpass(riser(sec["bars"] * BAR, rng), 7000), t0, gain=0.3)
        if kind == "drop":
            put(stems["fx"], IMP, t0, gain=0.8)
        # melodic content
        lead = sec.get("lead")
        if lead and kind == "drop":
            for s, d, p, v in retime(notes[lead], t0, sec["bars"]):
                put(stems["music"], pluck(p + 12 * (p < 62), d, v), s, pan=-0.1, gain=0.42)
        elif lead:
            for s, d, p, v in retime(notes[lead], t0, sec["bars"]):
                put(stems["music"], pluck(p + 12 * (p < 62), d, v * 0.7), s, pan=-0.15, gain=0.22)
        if kind in ("ambient", "break", "verse"):
            for s, d, p, v in retime(ghost, t0, sec["bars"]):
                put(stems["music"], ghost_note(p, d, v), s, pan=0.3 * np.sin(s), gain=0.09)
    # sidechain everything but drums to the kick (deep pump in the drops)
    duck = np.ones(n)
    env = 1 - 0.7 * np.exp(-np.arange(int(0.35 * SR)) / SR / 0.1)
    for kt in kicks:
        i = int(kt * SR)
        seg = duck[i:i + len(env)]
        np.minimum(seg, env[: len(seg)], out=seg)
    for k in ("bass", "music"):
        stems[k] *= duck[:, None]
    return stems, starts, total
