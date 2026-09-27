"""Assemble "Show Me the Receipt" (Kannaka Radio, quantum session, third iteration).

  python make_edm.py <moth.key> <elevenlabs.key>

Inputs already produced by quantum jobs (see output/song/song_provenance.json and output/edm/vocal_jobs.json):
lead takes A/B/C, the ghost voice, the graph-state groove, the hook's quantum chops, and one measured
retrocausal-echo impulse response. Vocals come from ElevenLabs text-to-speech (cached per line).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import edm, song, voice  # noqa: E402
from gsqs.lyrics import HOOK, SCRIPT  # noqa: E402
from gsqs.moth import Moth  # noqa: E402

ROOT = Path(__file__).parent
S1, SG, OUT = ROOT / "output" / "session-1", ROOT / "output" / "song", ROOT / "output" / "edm"
MOTH_KEY, EL_KEY = sys.argv[1], sys.argv[2]
SR = song.SR

patterns = song.groove_patterns(json.loads((SG / "graph_result.json").read_text())["result"]["output"])
stems, starts, total = edm.build({"A": S1 / "02_arrangement.mid", "B": SG / "take_B.mid", "C": SG / "take_C.mid"},
                                 S1 / "03_ghost.mid", patterns)
n = stems["drums"].shape[0]

# ---- vocals -------------------------------------------------------------------------------------
vox = np.zeros(n)
placed, prev_end = [], 0.0
hook_len = len(voice.line("KANNAKA", HOOK, OUT / "vocals_cache", EL_KEY)) / SR
for sec, bar, who, text in SCRIPT:
    x = voice.line(who, text, OUT / "vocals_cache", EL_KEY)
    x = song.highpass(x, 90)
    x = np.tanh(2.0 * x / (np.abs(x).max() + 1e-9)) / np.tanh(2.0)       # even out the lines
    if sec == "build" and text == HOOK:
        t = starts["drop"] - hook_len + 0.45        # the last word, "receipt", lands on the drop
    else:
        t = max(starts[sec] + bar * edm.BAR, prev_end + 0.25)
    i = int(t * SR)
    vox[i:i + len(x)] += x[: n - i] * (0.9 if who == "QE" else 1.0)
    prev_end = t + len(x) / SR
    placed.append({"t": round(t, 2), "who": who, "text": text})

# quantum chops of the hook (qrc-audio-v1), eight bars each
chops = np.zeros((n, 2))
for name, at in (("hook_chops_1.wav", starts["drop"]), ("hook_chops_2.wav", starts["drop"] + 8 * edm.BAR),
                 ("hook_chops_1.wav", starts["drop2"] + 8 * edm.BAR)):
    c = song.highpass(song.read_wav(OUT / name).mean(axis=1), 250)
    i = int(at * SR)
    c = c[: n - i]
    pan = np.sin(np.arange(len(c)) / SR * 2 * np.pi / (2 * edm.BAR)) * 0.5      # slow auto-pan
    chops[i:i + len(c), 0] += c * np.cos((pan + 1) * np.pi / 4)
    chops[i:i + len(c), 1] += c * np.sin((pan + 1) * np.pi / 4)

# ---- one quantum room: re-render the measured impulse response on the vocal and music stems ------
m = Moth(key_file=MOTH_KEY)
ir_asset = json.loads((SG / "echo_ir.json").read_text())["ir_asset"]
echo_jobs = {}


def quantum_echo(name, mono, mix):
    f = OUT / f"{name}_send.wav"
    song.write_wav(f, mono / (np.abs(mono).max() + 1e-9) * 0.89)
    tag = hashlib.sha256(f.read_bytes() + str(mix).encode()).hexdigest()[:12]
    cached = OUT / f"{name}_echo_{tag}.wav"
    if cached.exists():                       # same send, same IR: the render would be identical
        echo_jobs[name] = json.loads((OUT / f"{name}_echo_{tag}.json").read_text())["job_id"]
    else:
        job = m.run("retrocausal-echo-v1", {"bpm": edm.BPM, "mix": mix, "decay": 0.85},
                    {"audio": m.upload(f, "audio/wav"), "ir": ir_asset})
        m.download(job, "result", cached)
        (OUT / f"{name}_echo_{tag}.json").write_text(json.dumps({"job_id": job["job_id"]}))
        echo_jobs[name] = job["job_id"]
    w = song.read_wav(cached)
    out = np.zeros((n, 2))
    out[: min(n, len(w))] = w[:n]
    return out


vox_wet = quantum_echo("vocal", vox, 1.0)
music_wet = quantum_echo("music", stems["music"].mean(axis=1), 0.35)


def at_rms(x, target):
    active = x[np.abs(x).max(axis=1) > 1e-4] if x.ndim == 2 else x[np.abs(x) > 1e-4]
    return x * (target / (np.sqrt((active ** 2).mean()) + 1e-12))


# the music ducks ~4 dB under the voice so every word lands
env = np.convolve(np.abs(vox), np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
duck = 1 - 0.37 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
vox_st = np.stack([vox, vox], axis=1)
ir = song.reverb_ir(1.8)
parts = [
    at_rms(stems["drums"], 0.12),
    at_rms(stems["bass"], 0.11) * duck[:, None] ** 0.5,
    at_rms(music_wet, 0.075) * duck[:, None],
    at_rms(stems["fx"], 0.035),
    at_rms(vox_st, 0.10),
    at_rms(vox_wet, 0.022),
    at_rms(chops, 0.05),
]
room = song.convolve(parts[4] * 0.12 + parts[2] * 0.25, ir)
# section automation: drops hit hardest, builds hold back so the impact lands
auto = np.ones(n)
for s in edm.SECTIONS:
    a, b = int(starts[s["name"]] * SR), int((starts[s["name"]] + s["bars"] * edm.BAR) * SR)
    auto[a:b] = {"drop": 1.15, "build": 0.8}.get(s["kind"], 1.0)
auto = np.convolve(auto, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
mix = song.master([p * auto[: len(p), None] for p in parts + [room]], fade_s=4.0, drive=2.6)
final = OUT / "show_me_the_receipt.wav"
song.write_wav(final, mix)

(OUT / "edm_provenance.json").write_text(json.dumps({
    "title": "Show Me the Receipt", "artist": "Kannaka Radio (quantum session)", "bpm": edm.BPM,
    "key": "D dorian", "length_s": round(len(mix) / SR, 1),
    "form": [{"name": s["name"], "start_s": round(starts[s["name"]], 2), "bars": s["bars"]} for s in edm.SECTIONS],
    "vocals": {"provider": "ElevenLabs TTS", "model": voice.MODEL,
               "voices": {k: v["voice_id"] for k, v in voice.CAST.items()}, "lines": placed},
    "quantum": {"chops": json.loads((OUT / "vocal_jobs.json").read_text()), "echo_renders": echo_jobs,
                "echo_ir_measured_in": json.loads((SG / "echo_ir.json").read_text())["measured_in"],
                "wobble_rates_steps": [edm.wobble_rate(p) for p in patterns],
                "lead_takes_groove_randomness": "see output/song/song_provenance.json"},
    "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
}, indent=1), encoding="utf-8")
print(f"wrote {final.name}: {len(mix) / SR:.1f} s")
