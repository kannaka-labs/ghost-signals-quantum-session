"""One Ghost Signals quantum session: certified randomness -> seed motif -> quantum reservoir
arrangement -> quantum blur counter-voice -> local render -> quantum echo -> provenance card.

Every step's job id, engine, parameters, backend and file hash is recorded, so a listener can
audit how the track was made and anyone can re-run the chain.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .moth import Moth
from .music import compose_seed, notes_of, render


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pulse_from_job(m: Moth, job_id: str) -> dict:
    return m.get(f"/api/v1/jobs/{job_id}/result")["result"]["output"]


def fresh_pulse(m: Moth, num_qubits: int = 64) -> tuple[str, dict]:
    """Certified hardware randomness. 64 qubits: at 12 the counts-only readout's ordering charge
    exceeds the entropy and the engine (correctly) certifies zero bytes."""
    job = m.run("comet-qrng-v1", {"mode": "qpu", "num_qubits": num_qubits, "shots": 4096,
                                  "output_bytes": 32, "bell_witness": True})
    return job["job_id"], job["result"]["result"]["output"]


def run_session(m: Moth, out: Path, pulse_job: str | None = None, length: int = 32,
                log=print) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    card = {"title": "Ghost Signals quantum session", "made_at": datetime.now(timezone.utc).isoformat(),
            "steps": []}

    def step(name, **kw):
        card["steps"].append({"step": name, **kw})
        log(f"[{len(card['steps'])}] {name}: " + ", ".join(f"{k}={v}" for k, v in kw.items()
                                                          if k in ("job_id", "backend", "file", "notes")))

    # 1. certified randomness (reused or fresh)
    if pulse_job:
        pulse = pulse_from_job(m, pulse_job)
    else:
        pulse_job, pulse = fresh_pulse(m)
    rep, bw, prov = pulse["entropy_report"], pulse.get("bell_witness", {}), pulse["provenance"]
    if not pulse["random"].get("hex"):
        raise RuntimeError(f"pulse {pulse_job} delivered no certified bytes (grade {rep.get('grade')})")
    (out / "00_pulse.json").write_text(json.dumps(pulse, indent=1), encoding="utf-8")
    step("certified randomness", engine="comet-qrng-v1", job_id=pulse_job, backend=prov.get("backend"),
         grade=rep.get("grade"), h_bit=round(rep.get("h_bit", 0), 4), budget_bits=round(rep.get("budget_bits", 0)),
         bell_S=round(bw.get("S", 0), 3), bell_sigma=round(bw.get("sigma_S", 0), 3),
         pulse_hash=pulse.get("pulse", {}).get("pulse_hash"), random_hex=pulse["random"]["hex"])

    # 2. seed motif, every choice read from the certified bytes
    seed_mid, table = compose_seed(pulse["random"]["hex"])
    seed = out / "01_seed.mid"
    seed_mid.save(str(seed))
    step("seed motif (local)", file=seed.name, sha256=sha256(seed), notes=len(notes_of(seed)), table=table)

    # 3. quantum reservoir learns the motif and writes an arrangement
    seed_asset = m.upload(seed, "audio/midi")
    arr_job = m.run("qrc-midi-v1", {"length": length, "quality": "moderate", "bpm": 84, "loop": False},
                    {"midi": seed_asset})
    arr = m.download(arr_job, "result", out / "02_arrangement.mid")
    step("quantum reservoir arrangement", engine="qrc-midi-v1", job_id=arr_job["job_id"], file=arr.name,
         sha256=sha256(arr), notes=len(notes_of(arr)))

    # 4. quantum blur of the arrangement: the ghost counter-voice
    arr_asset = Moth.outputs(arr_job)["result"].get("output_asset_id") or m.upload(arr, "audio/midi")
    blur_job = m.run("blur-midi-v1", {"strength": 0.55, "reach": 0.35}, {"midi": arr_asset})
    ghost = m.download(blur_job, "result", out / "03_ghost.mid")
    step("quantum blur counter-voice", engine="blur-midi-v1", job_id=blur_job["job_id"], file=ghost.name,
         sha256=sha256(ghost), notes=len(notes_of(ghost)))

    # 5. local render: arrangement as lead, ghost as a softer, darker layer
    dry = render([(arr, 1.0, 0.45), (ghost, 0.45, 0.15)], out / "04_dry.wav")
    step("render (local additive synth)", file=dry.name, sha256=sha256(dry))

    # 6. quantum echo: a delay whose tap map was measured by scrambling and reversing a qubit chain
    dry_asset = m.upload(dry, "audio/wav")
    echo_job = m.run("retrocausal-echo-v1", {"bpm": 84, "mix": 0.55, "depth": 8, "negative_mode": "invert"},
                     {"audio": dry_asset})
    final = m.download(echo_job, "result", out / "05_ghost_signals_session.wav")
    taps = m.download(echo_job, "taps", out / "05_echo_taps.json")
    step("retrocausal echo", engine="retrocausal-echo-v1", job_id=echo_job["job_id"], file=final.name,
         sha256=sha256(final), taps_file=taps.name)

    (out / "provenance.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
    return card
