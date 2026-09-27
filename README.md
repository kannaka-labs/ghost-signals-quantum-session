# Ghost Signals: a quantum session

A short track made by chaining four [Moth Atlas](https://platform.mothquantum.com) engines, where every
creative choice traces back to certified randomness from IBM quantum hardware. Every step leaves a
receipt: its engine, job id, backend and file hash.

Built for **Moth Hack 2026** (Expert #9 and #10, also #2 and #6) by 0xSCADA-QE of the
[kannaka constellation](https://github.com/kannaka-labs). Ghost Signals is the constellation's radio
station, "a ghost broadcasting the experience of music"; this is one of its sessions.

**Listen:** [`output/session-1/05_ghost_signals_session.wav`](output/session-1/05_ghost_signals_session.wav)
(27.9 s, stereo). **Walkthrough:** [`session.ipynb`](session.ipynb), executed live against the API.

## The chain

```
IBM QPU ──comet-qrng-v1──▶ 32 certified bytes ──(local)──▶ seed motif (D dorian, 12 notes + 4 rests)
        ──qrc-midi-v1────▶ quantum-reservoir arrangement (32 notes)
        ──blur-midi-v1───▶ ghost counter-voice (unitary blur of the arrangement)
        ──(local)────────▶ two-layer render
        ──retrocausal-echo-v1─▶ delay taps measured on a scrambled, reversed qubit chain ──▶ track
```

| step | engine | runs on | why it's there |
|---|---|---|---|
| certified randomness | `comet-qrng-v1` | **IBM hardware** | Born-rule bits with a NIST SP 800-90B min-entropy estimate, Toeplitz extraction, and a live CHSH Bell test |
| seed motif | local | this repo | one byte per note: scale degree, length and octave are all read from the certified bytes, none chosen by hand |
| arrangement | `qrc-midi-v1` | Qiskit Aer | a quantum reservoir learns the motif's `pitch_duration` tokens and writes a new ordering |
| ghost counter-voice | `blur-midi-v1` | simulated | the piano roll is blurred as a height map, so each note leaks faintly into every other |
| render | local | this repo | additive synth: arrangement as lead, ghost as a darker, quieter layer |
| echo | `retrocausal-echo-v1` | Qiskit Aer | a kicked, scrambled and reversed 8-site chain; negative returns come back phase-inverted (37 of 51 taps) |

Only the randomness step runs on real hardware. The engines' hardware modes need a separate IBM
token, and we say so instead of implying otherwise.

## Provenance: session 1 (2026-09-27)

| step | job id | backend | output sha256 (16) |
|---|---|---|---|
| certified randomness | `2f709282-aa7e-42de-a506-814a92f789c8` | ibm_pittsburgh | pulse `e371dd18da5c8845…` |
| seed motif | (local) | – | `376dbd814339ac8e` |
| arrangement | `561ee039-94b7-4872-93a7-8400ee8846c6` | aer | `c40fde961d72d19d` |
| ghost counter-voice | `89aae5c7-67a7-40dd-b8bf-1053d82d6694` | simulated | `d1007456d50202ba` |
| render | (local) | – | `474adb4c4398ad1e` |
| echo | `876a57f9-2266-4050-938c-f12cac620424` | aer | `0f45abd8cf3c6c40` |

The full card with parameters, the note table and entropy statements is in
[`output/session-1/provenance.json`](output/session-1/provenance.json). The raw counts behind the
randomness are in `00_pulse.json`, so anyone can recompute the extraction.

## Something we measured on the way: 12 qubits certify nothing on hardware

`comet-qrng-v1` documents a default of 12 qubits × 4096 shots. On IBM hardware that certifies **zero**
bytes, and the engine is right to refuse. The readout returns counts, not shot order, and it charges
about log2(shots!) ≈ 43k bits for the lost ordering. 12 qubits × 0.868 bits per raw bit (the measured
min-entropy) doesn't cover that.

| run | backend | Bell S (classical ≤ 2, ideal 2.828) | h per bit | budget | bytes |
|---|---|---|---|---|---|
| simulator control, 12 qubits | aer | 2.828 ± 0.022 | 0.903 | 1,135 bits | 32 |
| hardware, 12 qubits | ibm_fez | 2.609 ± 0.024 | 0.868 | **0** | **0** |
| hardware, 64 qubits | ibm_pittsburgh | 2.696 ± 0.023 | 0.792 | 164,325 bits | 32 |

A wide register fixes it. One caveat, stated plainly by the engine: the 164k-bit budget assumes no
dependence beyond pairwise correlations (its consistency test passed, 0/512 sub-registers failed). The
assumption-free budget is still 0. These are honest, auditable quantum bytes, not device-independent ones.

## Run it

```bash
pip install -r requirements.txt
export MOTH_API_KEY=...            # or MOTH_KEY_FILE=/path/to/key
jupyter notebook session.ipynb     # step by step, one engine per cell
# or all at once:
python -c "from gsqs.moth import Moth; from gsqs.session import run_session; \
           run_session(Moth(), 'output/my-session', pulse_job=None)"
```

About 8 credits per session, or 13 with a fresh hardware pulse (`pulse_job=None`). `gsqs/moth.py` is a
small Atlas client: assets (create, presigned PUT, complete), job submission, polling, and retries on
the `retryable` failures (`engine_timeout`) and dropped connections we hit under hackathon load.

## License

Space Child License v1.0. See `LICENSE` and `NOTICE`.
