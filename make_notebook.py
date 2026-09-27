"""Build session.ipynb: the Atlas API workflow, one engine per cell (Moth Hack 2026, Expert #10)."""
import nbformat as nbf

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    md("""# Ghost Signals: a quantum session

A short track made by chaining four Moth Atlas engines, with every step's provenance kept.
[Ghost Signals](https://github.com/kannaka-labs) is the kannaka constellation's radio station: "a ghost
broadcasting the experience of music". This notebook is one of its sessions, made on quantum hardware
and quantum simulators, with a receipt for every step.

| step | engine | runs on |
|---|---|---|
| 1. certified randomness | `comet-qrng-v1` | **IBM quantum hardware** (Bell test + NIST SP 800-90B entropy report) |
| 2. seed motif | local | every pitch, octave and length read from the certified bytes |
| 3. arrangement | `qrc-midi-v1` | quantum reservoir computer (Qiskit Aer) learns the motif and writes 32 notes |
| 4. ghost counter-voice | `blur-midi-v1` | quantum blur scatters each note across the others |
| 5. render | local | two-layer additive synth |
| 6. echo | `retrocausal-echo-v1` | delay taps measured by scrambling and reversing a qubit chain (Aer) |

Set `MOTH_API_KEY` or point `KEY_FILE` at a key file. A full run costs about 8 credits (13 with a fresh pulse)."""),
    code("""import json, os, sys
from pathlib import Path
from IPython.display import Audio, Markdown, display

sys.path.insert(0, os.path.abspath("."))
from gsqs.moth import Moth
from gsqs.music import compose_seed, notes_of, render
from gsqs.session import pulse_from_job, fresh_pulse, sha256

KEY_FILE = os.environ.get("MOTH_KEY_FILE")          # or set MOTH_API_KEY
m = Moth(key_file=KEY_FILE)
OUT = Path("output/notebook-run"); OUT.mkdir(parents=True, exist_ok=True)
print("signed in as a", m.get("/api/v1/me")["platform_role"])"""),
    md("""## 1. Certified randomness from IBM hardware

`comet-qrng-v1` prepares qubits in |+⟩, measures them on an IBM QPU, and estimates the min-entropy the
device actually delivered before extracting any bytes. Eight extra qubits run four CHSH Bell pairs as a
live fidelity check.

**Use a wide register.** At the documented default of 12 qubits, the counts-only readout's charge for
lost shot order (~log2(shots!)) exceeds the entropy, and the engine correctly certifies **zero** bytes.
We measured exactly that on `ibm_fez` (S = 2.61, 0 bytes). 64 qubits clears it by a wide margin.

Set `PULSE_JOB = None` to pay for a fresh pulse (5 credits); by default this reuses the session's own."""),
    code("""PULSE_JOB = "2f709282-aa7e-42de-a506-814a92f789c8"   # 64 qubits on ibm_pittsburgh, 2026-09-27
pulse = pulse_from_job(m, PULSE_JOB) if PULSE_JOB else fresh_pulse(m, 64)[1]
rep, bell, prov = pulse["entropy_report"], pulse["bell_witness"], pulse["provenance"]
print(f"backend {prov['backend']}, grade {rep['grade']}")
print(f"min-entropy h = {rep['h_bit']:.3f} bits/bit, extractable budget {rep['budget_bits']:,.0f} bits")
print(f"Bell S = {bell['S']:.3f} ± {bell['sigma_S']:.3f}  (classical limit 2, ideal 2.828)")
for s in rep["statements"]:
    print(" -", s)
print("\\ncertified bytes:", pulse["random"]["hex"])"""),
    md("""## 2. A seed motif read from the bytes

One byte per note, D dorian: the low three bits pick the scale degree (7 is a rest), the next two the
length, one bit drops the octave. Nothing is chosen by hand."""),
    code("""seed_mid, table = compose_seed(pulse["random"]["hex"])
seed = OUT / "01_seed.mid"; seed_mid.save(str(seed))
names = "C C# D D# E F F# G G# A A# B".split()
print(" ".join(names[t["pitch"] % 12] + str(t["pitch"] // 12 - 1) if "pitch" in t else "·" for t in table))"""),
    md("""## 3. A quantum reservoir learns it

`qrc-midi-v1` trains a quantum reservoir on the motif's `pitch_duration` tokens and generates a new
32-note ordering. File inputs are assets: create, PUT to the presigned URL, complete, then pass the
asset id in `input_files`."""),
    code("""arr_job = m.run("qrc-midi-v1", {"length": 32, "quality": "moderate", "bpm": 84, "loop": False},
                {"midi": m.upload(seed, "audio/midi")})
arr = m.download(arr_job, "result", OUT / "02_arrangement.mid")
print("job", arr_job["job_id"], "->", len(notes_of(arr)), "notes")"""),
    md("""## 4. The ghost: a quantum blur

`blur-midi-v1` treats the piano roll as a height map and applies a unitary blur, so every note leaks
faintly into every other. The arrangement's output asset chains straight in; no re-upload."""),
    code("""arr_asset = Moth.outputs(arr_job)["result"]["output_asset_id"]
blur_job = m.run("blur-midi-v1", {"strength": 0.55, "reach": 0.35}, {"midi": arr_asset})
ghost = m.download(blur_job, "result", OUT / "03_ghost.mid")
print("job", blur_job["job_id"], "->", len(notes_of(ghost)), "ghost notes")"""),
    md("## 5. Render both voices"),
    code("""dry = render([(arr, 1.0, 0.45), (ghost, 0.45, 0.15)], OUT / "04_dry.wav")
display(Audio(str(dry)))"""),
    md("""## 6. Retrocausal echo

`retrocausal-echo-v1` kicks one site of a scrambled qubit chain, runs it backward, and turns the
signed response into a multi-tap delay: negative returns come back phase-inverted."""),
    code("""echo_job = m.run("retrocausal-echo-v1", {"bpm": 84, "mix": 0.55, "depth": 8, "negative_mode": "invert"},
                 {"audio": m.upload(dry, "audio/wav")})
final = m.download(echo_job, "result", OUT / "05_ghost_signals_session.wav")
taps = json.loads(m.download(echo_job, "taps", OUT / "05_echo_taps.json").read_text())
s = taps["extras"]["echo_summary"]
print(f"{taps['extras']['taps']} taps: {s['inverted']} inverted, {s['regular']} regular, {s['erased']} erased; "
      f"backend {taps['provenance']['backend']}")
display(Audio(str(final)))"""),
    md("## Provenance card"),
    code("""card = [("certified randomness", "comet-qrng-v1", PULSE_JOB, prov["backend"]),
        ("arrangement", "qrc-midi-v1", arr_job["job_id"], "aer"),
        ("ghost counter-voice", "blur-midi-v1", blur_job["job_id"], "simulated"),
        ("echo", "retrocausal-echo-v1", echo_job["job_id"], taps["provenance"]["backend"])]
rows = "\\n".join(f"| {a} | `{b}` | `{c}` | {d} |" for a, b, c, d in card)
display(Markdown("| step | engine | job id | backend |\\n|---|---|---|---|\\n" + rows +
                 f"\\n\\nfinal track sha256 `{sha256(final)}`"))"""),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
nbf.write(nb, "session.ipynb")
print("wrote session.ipynb with", len(cells), "cells")
