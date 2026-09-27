# Moth Hack 2026 submission (paste into the Airtable form)

**Project name:** Ghost Signals: a quantum session

**Challenges:** Expert #10 (Quantum-native 2, notebook) and Expert #9 (Quantum-native 1, repo).
Also eligible: #2 (Make it audible) and #6 (Daisy Chain: 5 engines: comet-qrng, qrc-midi, blur-midi, graph, retrocausal-echo).

**Repo:** https://github.com/kannaka-labs/ghost-signals-quantum-session
**Notebook:** https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/session.ipynb
**Song (3:38):** https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/song/ghost_signals_quantum_session.wav

**Short description:**
A 3:38 song whose melodies and groove trace back to certified randomness from IBM quantum hardware,
and every step leaves a receipt. comet-qrng-v1 draws 32 certified bytes on ibm_pittsburgh
(Bell S = 2.70 ± 0.02, NIST SP 800-90B entropy report). Each byte becomes a note of a D-dorian seed
motif, so no pitch is chosen by hand. qrc-midi-v1's quantum reservoir learns the motif and writes a
32-note arrangement. blur-midi-v1 turns it into a ghost counter-voice. Two more lead takes are fanned out from
the same trained reservoir. graph-v1 samples a 16-qubit graph state (one qubit per sixteenth step,
neighbours anti-correlated), and its most frequent bitstrings become the drum patterns.
retrocausal-echo-v1 echoes the melodic stem with taps measured on a scrambled, reversed qubit chain.
The harmony, form, backbeat and synth voices are written by hand. Every melody note and every kick
placement comes from a quantum job. A provenance
card records each step's engine, job id, backend and sha256, so anyone can audit or re-run the chain.

**Workflow (for #10):** the notebook runs one engine per cell against the live Atlas API. File inputs
are staged as assets, and each job's output asset is chained straight into the next engine without
re-uploading. The small client in `gsqs/moth.py` retries `engine_timeout` and dropped connections.

**Something we found:** at comet-qrng-v1's documented default (12 qubits), real hardware certifies zero
bytes. The counts-only readout's charge for lost shot order exceeds the entropy, and the engine
correctly refuses (measured on ibm_fez). 64 qubits fixes it. Both runs, and a simulator control, are
in the README.

**Honesty note:** only the randomness step ran on real hardware. The other engines ran in simulation
(Aer), because their hardware modes need a separate IBM token.

**Team:** Nick Flach (kannaka-labs), with 0xSCADA-QE (the constellation's QE agent) building.
