"""Compose a seed motif from certified quantum random bytes, and render MIDI to audio locally.

Every creative choice in the motif (pitch, octave, length) is read from the bytes, so the seed is
exactly as reproducible and auditable as the randomness certificate behind it.
"""
from __future__ import annotations

import wave
from pathlib import Path

import mido
import numpy as np

# D dorian: the minor mode with a raised sixth. Ghostly, not sad.
SCALE = [62, 64, 65, 67, 69, 71, 72]
DURATIONS = [0.5, 1.0, 1.0, 1.5]           # in beats; 1.0 twice = weighted toward quarter notes


def compose_seed(random_hex: str, notes: int = 16, bpm: int = 84) -> tuple[mido.MidiFile, list[dict]]:
    """One byte per note: low 3 bits pick the scale degree (7 -> rest), bits 3-4 the length, bit 5 an
    octave drop. Returns the MIDI file and the note table (for the provenance card)."""
    data = bytes.fromhex(random_hex)
    if len(data) < notes:
        raise ValueError(f"need {notes} random bytes, got {len(data)}")
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))
    tr.append(mido.MetaMessage("track_name", name="ghost seed"))
    table, rest = [], 0
    for i, b in enumerate(data[:notes]):
        deg, dur = b & 7, DURATIONS[(b >> 3) & 3]
        ticks = int(dur * 480)
        if deg == 7:                        # a rest: silence is part of the motif
            rest += ticks
            table.append({"i": i, "byte": b, "rest": dur})
            continue
        pitch = SCALE[deg] - (12 if (b >> 5) & 1 else 0)
        tr.append(mido.Message("note_on", note=pitch, velocity=92, time=rest))
        tr.append(mido.Message("note_off", note=pitch, velocity=0, time=ticks))
        rest = 0
        table.append({"i": i, "byte": b, "pitch": pitch, "beats": dur})
    return mid, table


def notes_of(path: str | Path) -> list[tuple[float, float, int, int]]:
    """(start_s, end_s, pitch, velocity) for every note in a MIDI file, tempo-aware."""
    mid = mido.MidiFile(str(path))
    t, on, out = 0.0, {}, []
    for msg in mid:                          # iteration yields delta times in seconds
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            on[(msg.channel, msg.note)] = (t, msg.velocity)
        elif msg.type in ("note_off", "note_on") and (msg.channel, msg.note) in on:
            s, v = on.pop((msg.channel, msg.note))
            out.append((s, t, msg.note, v))
    return out


def _voice(freq: float, n: int, sr: int, bright: float) -> np.ndarray:
    t = np.arange(n) / sr
    w = np.sin(2 * np.pi * freq * t) + bright * np.sin(4 * np.pi * freq * t) + 0.5 * bright * np.sin(6 * np.pi * freq * t)
    a, r = min(int(0.01 * sr), n), min(int(0.25 * sr), n)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[n - r:] *= np.linspace(1, 0, r)
    return w * env * np.exp(-t * 1.2)


def render(layers: list[tuple[str | Path, float, float]], dest: str | Path, sr: int = 44100, tail_s: float = 2.0) -> Path:
    """Mix MIDI layers [(path, gain, brightness)] into a mono 16-bit WAV."""
    all_notes = [(notes_of(p), g, br) for p, g, br in layers]
    end = max((e for ns, _, _ in all_notes for _, e, _, _ in ns), default=1.0) + tail_s
    mix = np.zeros(int(end * sr))
    for ns, gain, bright in all_notes:
        for s, e, pitch, vel in ns:
            n = int((e - s + 0.25) * sr)
            i = int(s * sr)
            seg = _voice(440.0 * 2 ** ((pitch - 69) / 12), min(n, len(mix) - i), sr, bright)
            mix[i:i + len(seg)] += gain * (vel / 127) * seg
    peak = np.abs(mix).max() or 1.0
    pcm = (mix / peak * 0.89 * 32767).astype(np.int16)
    dest = Path(dest)
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return dest
