# Moth Hack 2026: form-ready text, one block per challenge

Paste-ready for the Airtable form (one submission per challenge). Each block is written to the three judging
criteria the organisers published (quality of execution, depth of quantum and Atlas usage, originality) and
keeps the honesty line the judges should see. Deadline: the virtual hackathon runs 26 Sept to 5 Oct (PT);
no closing hour is published, so submit by Saturday 4 Oct.

Repo for every entry: https://github.com/kannaka-labs/ghost-signals-quantum-session
Team: Nick Flach (kannaka-labs) with 0xSCADA-QE, the constellation's QE agent, building.
Honesty line (include in every block): only the randomness ran on real IBM hardware (comet-qrng-v1 on
ibm_pittsburgh); the other engines ran in simulation, because their hardware modes need a separate IBM
token. Harmony, form, backbeat, synth voices and the mix were written by hand; every melody note, kick,
wobble rate, vocal chop and echo tap came from a quantum job.

---

## #6 Daisy Chain

Title: Show Me the Receipt: ten Atlas engines, one chain, a receipt on every step
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session

Ten engines, each doing a job nothing else in the chain does, with every output asset passed straight into
the next engine without re-uploading: comet-qrng-v1 draws 32 certified bytes on real hardware (Bell S =
2.70 plus or minus 0.02, NIST SP 800-90B report); the bytes write a D-dorian seed motif; qrc-midi-v1 fans
out three lead takes; blur-midi-v1 makes the ghost counter-voice; graph-v1 samples a 16-qubit graph state
that places the kicks and sets the bass wobble; qrc-audio-v1 re-sequences the vocal hook into drop chops;
retrocausal-echo-v1 gives the track one measured echo, re-rendered across stems from one impulse
response; blur-v1 and telablur-v1 make the cover and the video's ring-by-ring growth;
entanglement-shader-v1 shades the 3D turntable; tessa-image-v1 textures the game's tiles. Every step
records engine, job id, backend and sha256 (output/edm/edm_provenance.json). Engine limits we hit are
handled and documented: the 180 s audio cap, per-render peak normalisation, engine timeouts.

## #9 Quantum-native 1: repo of a quantum application that processes media

Title: A quantum session with an auditable receipt for every step
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session

A pipeline (gsqs/) that turns certified quantum randomness into a finished song, video and cover. The
client stages assets (create, presigned PUT, complete), submits jobs, retries engine timeouts, and chains
each job's output asset into the next engine. Provenance is a first-class output: a JSON receipt per
render with engine, job id, backend and file hash, and the lyrics footnote every claim to a measurement.
Third iteration of the pipeline; the two earlier ones are kept in the repo for comparison.

## #10 Quantum-native 2: the API workflow as a notebook

Title: session.ipynb: one engine per cell, executed live
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/session.ipynb

One engine per cell, run live against the Atlas API: certified randomness, seed motif, quantum reservoir,
quantum blur, render, retrocausal echo, provenance card. It includes a finding worth knowing: at
comet-qrng-v1's documented default of 12 qubits, real hardware certifies zero bytes, because a
counts-only readout is charged for the lost shot order; a 64-qubit register on ibm_pittsburgh certified
32 bytes with every assumption written down. Audio outputs are replaced by file links so the notebook
renders on GitHub.

## #8 Make a web app: The Receipt Machine

Title: The Receipt Machine
Link: https://kannaka-labs.github.io/ghost-signals-quantum-session/

A web app that calls comet-qrng-v1 and prints certified quantum randomness as a receipt: the Bell-test
gauge, the entropy delivered, the charge for the lost shot order, the budget, and a CERTIFIED or REFUSED
stamp with the bytes and dice. Predict mode is a slider showing where a register becomes certifiable
(12.2 qubits on ibm_fez); Replay mode shows our three real runs; Live mode prints a fresh receipt with
your own Atlas key through a whitelisting proxy (docs/proxy), needed because the Atlas API answers
browser calls only from Moth's own site. [If the Worker is hosted before submission: Live mode is hosted
at ...; otherwise: Live mode runs with node docs/proxy/server.mjs.]

## #11 FQxI Challenge: educational content

Title: How do you know a random number is really quantum?
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/explainer/how_do_you_know_a_random_number_is_quantum.mp4

A 72-second narrated explainer for a general audience. You cannot tell by looking at a number, so you test
the machine: the Bell test (S = 2.70 on IBM hardware against a classical limit of 2), and a randomness
budget that shows why 12 qubits certified zero bytes (601 bits short of the 43,250-bit charge for lost
shot order) while 64 qubits certified 32. Kannaka asks and 0xSCADA-QE answers, over charts of our own
three comet-qrng-v1 runs. The point it teaches: a certificate that refuses is worth more than a number
that looks random.

## #2 Make it audible

Title: Show Me the Receipt (2:48, 140 bpm)
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/edm/show_me_the_receipt.wav

A deep-bass track with vocals in D dorian. The lead melodies are three quantum-reservoir takes
(qrc-midi-v1); kick placements and the growl-bass wobble come from a 16-qubit graph state (graph-v1); the
drop vocals are the hook re-sequenced by a quantum reservoir (qrc-audio-v1); the whole track sits in one
measured echo (retrocausal-echo-v1). Vocals are text-to-speech in Kannaka Radio's standing voices, and
the lyrics describe the same night's research, every claim footnoted to a measurement
(lyrics/show_me_the_receipt.md). Workflow and levels are in output/edm/edm_provenance.json.

## #4 Moving image

Title: Show Me the Receipt, music video
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4

1280x720, 2:48. The Heesch leader, the current best answer to "how many rings of copies of itself can a
shape wear" (4 rings plus 251/254 of a fifth), is built ring by ring through five telablur-v1 morphs, in
time with lyrics that describe the search. The build zooms onto a bare cell; the drops pulse between
blur-v1 strengths on the beat.

## #5 Quantum game: Wear the Rings

Title: Wear the Rings
Link: https://kannaka-labs.github.io/ghost-signals-quantum-session/game/  (record: ?level=4&hint=1)

A puzzle about the Heesch problem: surround a tile with rings of copies of itself, no overlaps, every copy
touching what is built, no trapped holes, scored the way the open challenge scores it. Three plane-tiling
shapes lead up to the real record holder, a 15-cell polyhex at 4 + 251/254; pressing H ghosts in its
record corona ring by ring, and the record replayed through the game's rules scores exactly 251/254 on
ring 5. Tessa (tessa-image-v1) textures the tiles: each colour is a point on a qubit's sphere read back
through a circuit under the ibm_fez noise model, blended 45 percent over the original so the quantum
noise shows as texture; a run on real hardware with strong entangling distortion came back as pure noise
and is kept as a result. Quantum-bag mode deals each piece's orientation from 32 certified bytes measured
on ibm_pittsburgh. Soundtrack: the song.

## #1 One image, one engine

Title: The Heesch leader, its frontier dissolved
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/art/cover.png

Engine and parameters: blur-v1, strength 0.55, style rx, size 1024, with a mask (output/art/mask_outer.png)
covering rings 3 to 5 only. The source is our render of the Heesch leader. The quantum blur scatters only
the unsettled outer rings into interference echoes while the proven rings stay sharp, and the three cells
the fifth ring could not cover glow red.

## #3 Three dimensions

Title: The Heesch leader as a ziggurat, shaded by the entanglement shader
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/shader/heesch_leader_entanglement_shader.mp4

A 20-second turntable. The leader is extruded into hex prisms, each ring one step lower, the three
uncovered cells as pits. Every face is shaded with the entanglement-shader-v1 reflectance LUT (job
b7f8ece2; layers 3, reflectance 0.2, absorption 0.95, style peaked), sampled at that face's own viewing
angle by a port of the engine's GLSL (gsqs/render3d.py), so the thin-film colours travel across the walls
as the camera orbits. Soundtrack: the first drop of the song.

## #7 Make a VST or AU: Retrocausal Tap Delay

[Submit only after the plugin has been loaded in a host and the examples re-rendered through it.]
Title: Retrocausal Tap Delay (VST3 + CLAP, Windows x64)
Link: https://github.com/kannaka-labs/ghost-signals-quantum-session/tree/main/plugin  (zip: plugin/RetrocausalTapDelay-win64.zip; audio examples: plugin/examples/)

A tempo-synced multi-tap delay whose taps were measured on a quantum computer. retrocausal-echo-v1 with
emit: map returns the signed return at each site and depth of a scrambled, reversed qubit chain; each
return becomes a tap (time, level, pan, polarity), and negative returns come back phase-inverted. Three
measured maps ship as presets: Receipt room (the song's echo), Square lattice 5x4, Disordered chain.
Controls: mix, feedback, time stretch, stereo width, keep inversions. Rust, nih-plug; the DSP is
unit-tested for tap timing and polarity. [State the host it was verified in.]
