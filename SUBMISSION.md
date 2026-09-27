# Moth Hack 2026: submissions (one Airtable form per challenge)

Repo for every entry: https://github.com/kannaka-labs/ghost-signals-quantum-session
Team: Nick Flach (kannaka-labs), with 0xSCADA-QE, the constellation's QE agent, building.
Engines used across the project (10): comet-qrng-v1, qrc-midi-v1, blur-midi-v1, graph-v1,
retrocausal-echo-v1, qrc-audio-v1, blur-v1, telablur-v1, entanglement-shader-v1, tessa-image-v1.

Base URL for the file links below: `https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/`

---

## Expert #9 (Quantum-native 1): repo of a quantum application that processes media

**Project:** Show Me the Receipt: a Kannaka Radio quantum session
**Link:** the repo URL above

A pipeline that turns certified quantum randomness into a finished song, video and cover, where every
step leaves an auditable receipt (engine, job id, backend, sha256).
- comet-qrng-v1 draws 32 certified bytes on ibm_pittsburgh: Bell S = 2.70 ± 0.02, NIST SP 800-90B
  entropy report.
- Those bytes write a D-dorian seed motif.
- qrc-midi-v1 trains a quantum reservoir on the motif and fans out three lead takes.
- graph-v1 samples a 16-qubit graph state whose bitstrings place the kicks and set the bass wobble.
- qrc-audio-v1 re-sequences the vocal hook into drop chops.
- retrocausal-echo-v1 gives the whole track one measured echo.
- blur-v1 and telablur-v1 make the cover and the video's ring-by-ring growth.

Engine limits we hit are handled in the client and documented: the 180 s audio cap (split the stem and
reuse the measured impulse response), per-render peak normalisation (undone by measured dry gain), and
engine_timeout retries.

## Expert #10 (Quantum-native 2): notebook of the API workflow

**Link:** `session.ipynb` (base URL + `session.ipynb`)

One engine per cell, executed live against the Atlas API. It stages assets (create, presigned PUT,
complete), then chains each job's output asset straight into the next engine: certified randomness,
seed motif, quantum reservoir, quantum blur, render, retrocausal echo, and a provenance card. It
includes a finding: at comet-qrng-v1's documented default of 12 qubits, real hardware certifies zero
bytes.

## #2 (Make it audible)

**Audio:** `output/edm/show_me_the_receipt.wav` (2:48)
**Workflow:** a 140 bpm half-time deep-bass track in D dorian.
- The lead melodies are three quantum-reservoir takes (qrc-midi-v1).
- The kick placements and the growl-bass wobble rate come from a 16-qubit graph state (graph-v1).
- The drop vocals are the hook re-sequenced by a quantum reservoir (qrc-audio-v1).
- Everything sits in one room: an echo measured by scrambling and reversing a qubit chain
  (retrocausal-echo-v1).
- Vocals are ElevenLabs TTS in Kannaka Radio's standing voices. The lyrics describe the same night's
  research, and every claim is footnoted to a measurement (`lyrics/show_me_the_receipt.md`).

## #6 (Daisy Chain)

**Engines: 10**, each doing a job nothing else in the chain does:
- comet-qrng-v1: the seed;
- qrc-midi-v1: three lead takes;
- blur-midi-v1: the ghost counter-voice;
- graph-v1: the groove and the wobble;
- qrc-audio-v1: the vocal chops;
- retrocausal-echo-v1: the echo, one impulse response re-rendered across stems;
- blur-v1: the cover and the drop pulses;
- telablur-v1: the ring-to-ring morphs;
- entanglement-shader-v1: the 3D material;
- tessa-image-v1: the game sprites.

Output assets chain directly into the next engine, without re-uploading.

## #4 (Moving image)

**Video:** `output/video/show_me_the_receipt.mp4` (1280×720, 2:48)

The Heesch leader, the current best answer to "how many rings of copies of itself can a shape wear?"
(4 rings plus 251/254 of a fifth), is built ring by ring through five telablur-v1 morphs, in time with
lyrics that describe the search. The build zooms onto a bare cell. The drops pulse between blur-v1
strengths on the beat.

## #1 (One image, one engine)

**Image:** `output/art/cover.png`
**Engine and parameters:** blur-v1, `strength 0.55, style "rx", size 1024`, with a mask
(`output/art/mask_outer.png`) covering rings 3–5 only. The source is our render of the Heesch leader.
The quantum blur scatters only the unsettled frontier into interference echoes, while the rings that
are proven stay sharp. The three cells the fifth ring could not cover glow red.

## #8 (Make a web app): The Receipt Machine

**Link:** https://kannaka-labs.github.io/ghost-signals-quantum-session/

A web app that calls the Atlas API (comet-qrng-v1) and prints certified quantum randomness as a
receipt: the Bell-test gauge, the entropy delivered, the charge for the lost shot order, the budget,
and a CERTIFIED / REFUSED stamp with the bytes and dice.
- **Predict** mode is an interactive slider showing where a register becomes certifiable (12.2
  qubits on ibm_fez).
- **Replay** mode shows our three real runs.
- **Live** mode prints a fresh receipt with your own Atlas key, through a whitelisting proxy
  (`docs/proxy`, as a Cloudflare Worker or `node docs/proxy/server.mjs`). The proxy is needed because
  the Atlas API only answers browser calls from Moth's own site.

## #5 (Quantum game): Wear the Rings (eligible for the Global Quantum Game Jam)

**Play:** https://kannaka-labs.github.io/ghost-signals-quantum-session/game/
**Deep link to the record:** https://kannaka-labs.github.io/ghost-signals-quantum-session/game/?level=4&hint=1

A puzzle game about the Heesch problem. You surround a tile with rings of copies of itself: no overlaps,
every copy touching what's built, no trapped holes. Your score is Yukon's own (complete rings plus the
fraction of the next ring). Three shapes that tile the plane lead up to the real record holder, a
15-cell polyhex at 4 + 251/254 = 4.9882, and pressing H ghosts in its record corona ring by ring. We
replayed the record through the game's rules: rings 1–4 close cleanly and ring 5 scores 251/254.
- **Tessa (tessa-image-v1)** paints the tile sprites. Each colour is encoded on a qubit's sphere, with
  entangling distortion gates, and read back through a circuit on IBM hardware (job 404cf1aa). At the
  time of writing that job was still in IBM's queue, and the game shows the pre-quantum sprites until
  its result is committed.
- **Quantum bag** mode deals each piece's orientation from 32 certified random bytes measured on
  ibm_pittsburgh (comet-qrng-v1). No rotating: you place what the qubits give you.
- The soundtrack is the song.

## #7 (Make a VST or AU): Retrocausal Tap Delay

**Plugin:** `plugin/RetrocausalTapDelay-win64.zip` (VST3 + CLAP, Windows x64; source in `plugin/`)
**Audio examples:** `plugin/examples/`, the song's hook vocal and quantum melody through each preset

A tempo-synced multi-tap delay whose taps were measured on a quantum computer. retrocausal-echo-v1 with
`emit: map` returns the signed return at each site and depth of a scrambled, reversed qubit chain.
Each return becomes a tap (time, level, pan, polarity), and negative returns come back
phase-inverted. It ships three measured maps as presets: Receipt room (the song's echo), Square lattice
5×4, and Disordered chain. The controls are mix, feedback, time stretch, stereo width, and "keep
inversions". Written in Rust with nih-plug. The DSP is unit-tested (tap timing and polarity), and the
DLL exports the VST3 and CLAP entry points. It has not been loaded in a DAW on our machine yet.

## #3 (Three dimensions)

**Video:** `output/shader/heesch_leader_entanglement_shader.mp4` (20 s turntable, 1280×720)

The Heesch leader is extruded into a 3D ziggurat of hex prisms: each ring is one step lower, and the
three cells no copy could cover are pits. Every face is shaded with the entanglement-shader-v1
reflectance LUT (job b7f8ece2; `layers 3, reflectance 0.2, absorption 0.95, style peaked`), sampled at
that face's own viewing angle by a port of the engine's GLSL (`gsqs/render3d.py`). The thin-film
colours travel across the walls as the camera orbits. The soundtrack is the first drop of the song.

## Guest: FQxI Challenge (#11)

**Video:** `output/explainer/how_do_you_know_a_random_number_is_quantum.mp4` (72 s, narrated)

"How do you know a random number is really quantum?" You can't tell by looking at it, so you test the
machine. Kannaka asks and 0xSCADA-QE answers, over charts of our own three comet-qrng-v1 runs:
- the Bell test (S = 2.70 on IBM hardware against a classical limit of 2);
- a randomness budget showing why 12 qubits certified zero bytes (601 bits short of the 43,250-bit
  charge for lost shot order), while 64 qubits certified 32 bytes with every assumption written down.

**Honesty note (applies to every entry):**
- Only the randomness ran on real quantum hardware.
- The other engines ran in simulation (Aer or statevector), because their hardware modes need a
  separate IBM token.
- Written by hand: harmony, form, backbeat, synth voices and the mix.
- Every melody note, kick placement, wobble rate, vocal chop and echo tap comes from a quantum job.
