"""Assemble "Ghost Signals (quantum session)": the full song, from the quantum material in output/.

  python make_song.py            # needs output/song/{take_B,take_C}.mid + graph_result.json (see README)
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import song  # noqa: E402
from gsqs.moth import Moth  # noqa: E402

ROOT = Path(__file__).parent
S1, OUT = ROOT / "output" / "session-1", ROOT / "output" / "song"
jobs = json.loads((OUT / "jobs.json").read_text())
graph = json.loads((OUT / "graph_result.json").read_text())["result"]["output"]
patterns = song.groove_patterns(graph)
print("groove patterns:", patterns)

takes = {"A": S1 / "02_arrangement.mid", "B": OUT / "take_B.mid", "C": OUT / "take_C.mid"}
stems, melodic, smap = song.build(takes, S1 / "03_ghost.mid", patterns)

# quantum echo on the melodic stem only, so the drums stay tight
mono = melodic.mean(axis=1)
mono = mono / (np.abs(mono).max() + 1e-9) * 0.89
# The engine caps audio at 180 s. An echo is linear, so echoing two halves with the SAME measured
# impulse response and summing them at their offsets equals echoing the whole: the first job measures
# the response, the second re-renders with it (its `ir` output asset), so the echo is one measurement.
split = int(next(s["start_s"] for s in smap if s["name"] == "breakdown") * song.SR)
m = Moth(key_file=sys.argv[1] if len(sys.argv) > 1 else None)
params = {"bpm": song.BPM, "mix": 0.5, "depth": 8, "negative_mode": "invert", "decay": 0.85}
wet = np.zeros((len(mono) + 8 * song.SR, 2))
# Reuse the impulse response already measured (job f103da4a) so every render carries the same echo;
# set MEASURE_NEW_IR=1 to pay for a fresh measurement instead.
import os  # noqa: E402
echo_jobs = []
ir_asset = None if os.environ.get("MEASURE_NEW_IR") else json.loads((OUT / "echo_ir.json").read_text())["ir_asset"] \
    if (OUT / "echo_ir.json").exists() else None
for i, (a, b) in enumerate(((0, split), (split, len(mono)))):
    part = OUT / f"melodic_dry_{i + 1}.wav"
    song.write_wav(part, mono[a:b])
    files = {"audio": m.upload(part, "audio/wav")}
    if ir_asset:
        files["ir"] = ir_asset
    job = m.run("retrocausal-echo-v1", params, files)
    echo_jobs.append(job["job_id"])
    if not ir_asset:
        ir_asset = Moth.outputs(job)["ir"]["output_asset_id"]
        (OUT / "echo_ir.json").write_text(json.dumps({"ir_asset": ir_asset, "measured_in": job["job_id"]}))
    m.download(job, "result", OUT / f"melodic_echo_{i + 1}.wav")
    m.download(job, "taps", OUT / f"melodic_echo_taps_{i + 1}.json")
    seg = song.read_wav(OUT / f"melodic_echo_{i + 1}.wav")
    # the engine peak-normalises each render, so undo it: scale by the dry signal's gain inside the wet
    dry = mono[a:b]
    k = min(len(dry), len(seg))
    g = float((seg[:k, 0] * dry[:k]).sum() / (dry[:k] ** 2).sum())
    seg = seg * (0.3 / g)
    print(f"  part {i + 1}: engine gain {g:.3f} -> rescaled to 0.300")
    wet[a:a + len(seg)] += seg[: len(wet) - a]
    print(f"echo part {i + 1}: job {job['job_id']}, {len(seg) / song.SR:.1f} s")
t1 = json.loads((OUT / "melodic_echo_taps_1.json").read_text())["extras"]
t2 = json.loads((OUT / "melodic_echo_taps_2.json").read_text())["extras"]
print("same tap map on both halves:", t1.get("taps") == t2.get("taps") and t1.get("echo_summary") == t2.get("echo_summary"))
echo = {"job_id": echo_jobs}


def at_rms(x, target):
    active = x[np.abs(x).max(axis=1) > 1e-4]
    r = np.sqrt((active ** 2).mean()) if len(active) else 1.0
    return x * (target / (r + 1e-12))


# stem balance: melody on top, then drums and bass, pad underneath; room reverb on pad + melody
ir = song.reverb_ir()
pad = at_rms(stems["pad"], 0.055)
mel = at_rms(wet, 0.13)
room = song.convolve(pad * 0.6 + mel[: len(pad)] * 0.25, ir) if len(mel) >= len(pad) else song.convolve(pad * 0.6, ir)
parts = [at_rms(stems["drums"], 0.10), at_rms(stems["bass"], 0.085), pad, mel, room]
# section envelope: the breakdown drops back so the return lands (0.25 s ramps at the edges)
env = np.ones(max(len(p) for p in parts))
for s in smap:
    if s["name"] == "breakdown":
        a, b = int(s["start_s"] * song.SR), int((s["start_s"] + s["bars"] * song.BAR) * song.SR)
        r = int(0.25 * song.SR)
        env[a:b] = 0.6
        env[a - r:a] = np.linspace(1, 0.6, r)
        env[b:b + r] = np.linspace(0.6, 1, r)
parts = [p * env[: len(p), None] for p in parts]
mix = song.master(parts)
final = OUT / "ghost_signals_quantum_session.wav"
song.write_wav(final, mix)

card = {
    "title": "Ghost Signals (quantum session)",
    "length_s": round(len(mix) / song.SR, 1),
    "bpm": song.BPM,
    "key": "D dorian",
    "form": smap,
    "quantum_sources": {
        "certified_randomness": {"engine": "comet-qrng-v1", "job_id": "2f709282-aa7e-42de-a506-814a92f789c8",
                                 "backend": "ibm_pittsburgh", "used_for": "seed motif; take B/C and groove seeds"},
        "lead_A": {"engine": "qrc-midi-v1", "job_id": "561ee039-94b7-4872-93a7-8400ee8846c6", "trained_on": "seed motif"},
        "lead_B": {"engine": "qrc-midi-v1", **jobs["take_B"], "model": "fan-out of lead_A's trained reservoir"},
        "lead_C": {"engine": "qrc-midi-v1", **jobs["take_C"], "model": "fan-out of lead_A's trained reservoir"},
        "ghost": {"engine": "blur-midi-v1", "job_id": "89aae5c7-67a7-40dd-b8bf-1053d82d6694", "of": "lead_A"},
        "groove": {"engine": "graph-v1", "job_id": jobs["graph"], "mode": "emu", "patterns": patterns},
        "echo": {"engine": "retrocausal-echo-v1", "job_id": echo["job_id"], "on": "melodic stem, two halves (180 s cap)",
                 "ir_measured_in": json.loads((OUT / "echo_ir.json").read_text())["measured_in"],
                 "note": "both halves re-render one measured impulse response; per-render peak normalisation undone"},
    },
    "local": "harmony (Dm7 Cmaj7 G7 Dm7), form, bass/pad/drum synthesis, mix: gsqs/song.py",
    "sha256": hashlib.sha256(final.read_bytes()).hexdigest(),
}
(OUT / "song_provenance.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print(f"wrote {final.name}: {card['length_s']} s, sha256 {card['sha256'][:16]}")
