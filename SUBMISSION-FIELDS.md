# Moth Hack 2026: what to put in each form field

Form: https://airtable.com/appsrkUE9iVgeGsH5/pagdAHP56ovMdYX7x/form
**Deadline: Monday 5 October 2026, 11:59 PM Pacific.** Submit one form per entry. Ten entries are ready below. #7, the plugin, is held until it has been loaded in a DAW.

## The same in every form

**Tell us about yourself / team**

| Field | What to enter |
|---|---|
| Team or individual | Team |
| Team's name | Kannaka Labs |
| Main contact email | your email |
| Discord handle | your handle on the Moth Discord |
| GitHub handle | flaukowski |
| Team details | Nick Flach (kannaka-labs), plus 0xSCADA-QE, the constellation's QE agent (an AI agent running on Claude in Claude Code), which built the code, the media and the documentation under Nick's direction. |
| Other | https://github.com/kannaka-labs |

**About the project**

| Field | What to enter |
|---|---|
| QPU or emulation | Both. comet-qrng-v1 ran on real IBM hardware (ibm_pittsburgh). The other engines ran in emulation (Qiskit Aer), because their hardware modes need a separate IBM token. |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session (unless the entry below gives a more specific link) |
| Generative AI usage | Yes (tick it) |
| What generative AI tools | Claude (Anthropic) in Claude Code; ElevenLabs (voices) |
| Non-Moth APIs | Tick it only where the entry says so. |

**Last bits:** the three confirmations (eligibility and rights, permission to show your work, permission for teammates' details) are yours to tick. "Keep in touch" is your choice.

All media links point to files in the public repo. GitHub plays the .mp4 files in the browser.

---

## Entry 1 of 10: #6 Daisy Chain

| Field | What to enter |
|---|---|
| Project title | Show Me the Receipt: ten Atlas engines, one chain, a receipt on every step |
| Elevator pitch | Ten Atlas engines chained output-to-input turn certified quantum randomness from IBM hardware into a song, a video, a game and a 3D render, with a hashed receipt for every step. |
| Challenge | Daisy Chain (#6) |
| Engines used | comet-qrng-v1, qrc-midi-v1, blur-midi-v1, graph-v1, qrc-audio-v1, retrocausal-echo-v1, blur-v1, telablur-v1, entanglement-shader-v1, tessa-image-v1 |
| Demo URL | https://kannaka-labs.github.io/ghost-signals-quantum-session/ |
| Non-Moth APIs | Yes. ElevenLabs text-to-speech, through our own ElevenLabs key, for the sung and spoken vocals. Our client calls its REST API; the vocals then go through qrc-audio-v1 and retrocausal-echo-v1. |
| Poster art (upload) | output/art/cover.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4 |
| Additional images | output/shader/game_l4.png, output/shader/webapp_shot.png |

**Project description**

> Show Me the Receipt is one creative chain across ten Atlas engines. Each engine does a job nothing else in the chain does, and each one's output asset passes straight into the next without re-uploading. Real quantum hardware on IBM's ibm_pittsburgh draws 32 bytes of certified randomness, with a passed Bell test and a NIST SP 800-90B entropy report. Those bytes write a seed motif in D dorian. A quantum reservoir improvises three lead takes, and a quantum blur turns one of them into a ghost counter-voice. A 16-qubit graph state places the kicks and sets the bass wobble. A second reservoir re-sequences the vocal hook into drop chops. The whole track sits in one measured echo. The same chain makes the cover, the music video, a 3D turntable and the tiles of a browser game. Our motivation was provenance: every step records the engine, job id, backend and a file hash, so anyone can check where each note came from.

**Technical description**

> Python client (gsqs/) for the Atlas REST API. It stages assets (create, presigned PUT, complete), submits jobs, polls, retries engine timeouts and chains output assets by id. comet-qrng-v1 ran on ibm_pittsburgh (64 qubits); the other nine engines ran on Qiskit Aer. Engine limits we hit are handled and documented: the 180-second audio cap, per-render peak normalisation, and timeouts. Every render writes a JSON receipt (output/edm/edm_provenance.json).

## Entry 2 of 10: #9 Quantum-native 1 (a repo that processes media)

| Field | What to enter |
|---|---|
| Project title | A quantum media session with an auditable receipt for every step |
| Elevator pitch | An open-source pipeline that turns certified quantum randomness into a finished song, cover and video, with a hashed provenance receipt for every engine call. |
| Challenge | Quantum-native 1 (#9) |
| Engines used | comet-qrng-v1, qrc-midi-v1, blur-midi-v1, graph-v1, qrc-audio-v1, retrocausal-echo-v1, blur-v1, telablur-v1 |
| Demo URL | https://kannaka-labs.github.io/ghost-signals-quantum-session/ |
| Non-Moth APIs | Yes. ElevenLabs text-to-speech, through our own key, for the vocals that the pipeline then processes with qrc-audio-v1 and retrocausal-echo-v1. |
| Poster art (upload) | output/art/cover.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4 |

**Project description**

> This is a repository that turns quantum measurements into finished media, and keeps the receipts. Certified random bytes from real IBM hardware write a seed motif. From there, Atlas engines improvise melodies, place drums, chop vocals and add an echo, ending in a mixed track, a cover image and a music video. The repo is a working tool, not a one-off. You run one command for a session (make_song.py, make_edm.py), and the notebook shows the same workflow cell by cell. Provenance is a first-class output. Every render writes a JSON receipt with the engine, job id, backend and file hash, and the lyrics footnote each claim to a measurement. The repo keeps all three iterations of the pipeline, a short session, a full song and the final track, so the development is visible. It also keeps the failures we found, such as the default QRNG settings certifying zero bytes on hardware.

**Technical description**

> Python 3, standard library plus numpy. gsqs/moth.py is the Atlas client: asset staging through presigned uploads, job submission and polling, retries on engine_timeout and dropped connections, and output-asset chaining. gsqs/session.py, song.py and edm.py build the arrangements, and gsqs/voice.py handles vocals. Engines: comet-qrng-v1 on ibm_pittsburgh; qrc-midi-v1, blur-midi-v1, graph-v1, qrc-audio-v1, retrocausal-echo-v1, blur-v1 and telablur-v1 on Qiskit Aer.

## Entry 3 of 10: #10 Quantum-native 2 (the workflow as a notebook)

| Field | What to enter |
|---|---|
| Project title | session.ipynb: one Atlas engine per cell, executed live |
| Elevator pitch | A notebook that runs a whole quantum music session against the Atlas API, one engine per cell, and shows why the QRNG's default settings certify nothing on real hardware. |
| Challenge | Quantum-native 2 (#10) |
| Engines used | comet-qrng-v1, qrc-midi-v1, blur-midi-v1, retrocausal-echo-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/session.ipynb |
| Demo URL | https://nbviewer.org/github/kannaka-labs/ghost-signals-quantum-session/blob/main/session.ipynb |
| Non-Moth APIs | No |
| Poster art (upload) | output/demos/shots/notebook.png (or output/art/cover.png) |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/demos/demo_notebook.mp4 |

**Project description**

> The notebook walks the Atlas API workflow one engine per cell, executed live: certified randomness, a seed motif, a quantum reservoir, a quantum blur, a render, a retrocausal echo and a provenance card. Every cell shows the request, the job id, the backend and the output, so a reader can repeat it with their own key. It also records a finding worth knowing. At comet-qrng-v1's documented default of 12 qubits, real hardware certifies zero bytes, because a counts-only readout is charged for the lost shot order. A 64-qubit register on ibm_pittsburgh certified 32 bytes, with every assumption written down. Audio outputs are replaced by file links, so the notebook renders on GitHub and nbviewer. We wanted a notebook that teaches the API by doing real work, and that is honest about what the certificate does and does not prove.

**Technical description**

> A Jupyter notebook over the repo's gsqs client: asset upload through presigned URLs, job submission and polling, and outputs chained by asset id. comet-qrng-v1 ran on IBM hardware (ibm_pittsburgh, 64 qubits) with its NIST SP 800-90B entropy report shown inline. qrc-midi-v1, blur-midi-v1 and retrocausal-echo-v1 ran on Qiskit Aer. The final cell writes a provenance card: engine, job id and backend per step, plus the track's sha256.

## Entry 4 of 10: #8 Make a web app

| Field | What to enter |
|---|---|
| Project title | The Receipt Machine |
| Elevator pitch | A web app that prints certified quantum randomness as a till receipt, and shows when a quantum random number generator should refuse to certify anything. |
| Challenge | Make a web app (#8) |
| Engines used | comet-qrng-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session/tree/main/docs |
| Demo URL | https://kannaka-labs.github.io/ghost-signals-quantum-session/ |
| Non-Moth APIs | No |
| Poster art (upload) | output/shader/webapp_shot.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/demos/demo_web_app.mp4 |

**Project description**

> The Receipt Machine calls comet-qrng-v1 and prints the result as a receipt. It shows the Bell-test gauge, the entropy delivered, the charge for the lost shot order, the remaining budget, and a CERTIFIED or REFUSED stamp with the bytes turned into dice. Predict mode is a slider showing the register size at which hardware becomes certifiable (12.2 qubits on ibm_fez). Replay mode shows our three real hardware runs. Live mode prints a fresh receipt with your own Atlas key. The point is that a quantum random number generator should be able to say no. At the documented default settings, our hardware run came back REFUSED, and the app shows exactly why, line by line, like a till receipt.

**Technical description**

> A static single-page app (HTML, CSS and JavaScript) on GitHub Pages; Predict and Replay need no key. Live mode calls comet-qrng-v1 through a small whitelisting proxy (docs/proxy: a Cloudflare Worker or a local Node server), because the Atlas API accepts browser calls only from Moth's own site. The entropy accounting follows comet-qrng-v1's own report: min-entropy per shot, the log2(shots!) charge for lost order, and the extractor output.

## Entry 5 of 10: #11 FQxI Challenge (educational content)

| Field | What to enter |
|---|---|
| Project title | How do you know a random number is really quantum? |
| Elevator pitch | A 72-second narrated explainer: you can't tell by looking at a number, so you test the machine, and sometimes the honest answer is "certified zero bytes". |
| Challenge | FQxI Challenge (#11) |
| Engines used | comet-qrng-v1 |
| Demo URL | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/explainer/how_do_you_know_a_random_number_is_quantum.mp4 |
| Non-Moth APIs | Yes. ElevenLabs text-to-speech, through our own key, for the two narrating voices. |
| Poster art (upload) | output/explainer/peek_44.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/explainer/how_do_you_know_a_random_number_is_quantum.mp4 |

**Project description**

> A 72-second narrated explainer for a general audience. Looking at a number can't tell you whether it is quantum random, so you test the machine that made it. The video explains the Bell test with our own measurement on IBM hardware: S = 2.70, against a classical limit of 2. It then explains the randomness budget. At 12 qubits the hardware run certified zero bytes, 601 bits short of the charge for lost shot order, while 64 qubits certified 32 bytes. Two voices carry it, one asking and one answering, over charts of our three real comet-qrng-v1 runs. The idea it teaches is that a certificate that refuses is worth more than a number that merely looks random. We made it because most "quantum random" claims skip the part where you check.

**Technical description**

> The charts come from three real comet-qrng-v1 jobs (two on ibm_fez, one on ibm_pittsburgh), read from each job's entropy report: Bell S, min-entropy per shot, and the lost-order charge. Built in Python (make_explainer.py): frames drawn with Pillow for each line of the script, two ElevenLabs voices, and ffmpeg assembly at 1280x720. Every number on screen comes from our own three runs (output/explainer/runs.json).

## Entry 6 of 10: #2 Make it audible

| Field | What to enter |
|---|---|
| Project title | Show Me the Receipt (2:48, 140 bpm) |
| Elevator pitch | A deep-bass track whose melodies, kicks, wobble, vocal chops and echo were all measured from quantum jobs, with lyrics footnoted to the research behind them. |
| Challenge | Make it audible (#2) |
| Engines used | comet-qrng-v1, qrc-midi-v1, graph-v1, qrc-audio-v1, retrocausal-echo-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session |
| Demo URL | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/edm/show_me_the_receipt.wav |
| Non-Moth APIs | Yes. ElevenLabs text-to-speech, through our own key, for the vocals (Kannaka Radio's standing voices). |
| Poster art (upload) | output/art/cover.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4 |

**Project description**

> Show Me the Receipt is a deep-bass track with vocals in D dorian, at 140 bpm half-time, lasting 2:48. The lead melodies are three quantum-reservoir takes from qrc-midi-v1, seeded by certified random bytes from IBM hardware. The kick placements and the growl-bass wobble come from the most likely bitstrings of a 16-qubit graph state (graph-v1). The drop vocals are the hook re-sequenced by a quantum reservoir (qrc-audio-v1), and the whole track sits inside one measured echo (retrocausal-echo-v1). Harmony, form, backbeat, synth voices and the mix were written by hand. Every melody note, kick, wobble rate, vocal chop and echo tap came from a quantum job. The lyrics describe the same night's research, with every claim footnoted to a measurement (lyrics/show_me_the_receipt.md).

**Technical description**

> Python (make_edm.py, gsqs/edm.py) renders and mixes at 44.1 kHz. qrc-midi-v1 is fanned out from one trained model asset; graph-v1 is a 16-qubit chain with ZZ = -0.6; qrc-audio-v1 chops at one-eighth-note chunks; retrocausal-echo-v1 renders are rescaled to undo per-render peak normalisation. Workflow and levels: output/edm/edm_provenance.json. Simulation for all but the QRNG.

## Entry 7 of 10: #4 Moving image

| Field | What to enter |
|---|---|
| Project title | Show Me the Receipt, music video |
| Elevator pitch | A shape that tries to surround itself with copies of itself, built ring by ring through quantum-blur morphs, in time with a song about the search. |
| Challenge | Moving image (#4) |
| Engines used | telablur-v1, blur-v1 (soundtrack: qrc-midi-v1, graph-v1, qrc-audio-v1, retrocausal-echo-v1, comet-qrng-v1) |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session |
| Demo URL | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4 |
| Non-Moth APIs | Yes. ElevenLabs text-to-speech, through our own key, for the vocals in the soundtrack. |
| Poster art (upload) | output/video/peek_95.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/video/show_me_the_receipt.mp4 |

**Project description**

> A 2:48 music video at 1280x720. Its subject is the Heesch leader, the current best answer to "how many rings of copies of itself can a shape wear without gaps?": 4 full rings plus 251 of the 254 cells of a fifth. The video builds it ring by ring through five telablur-v1 morphs, in time with lyrics describing the search. The build zooms onto a bare cell where the fifth ring fails. In the drops, the image pulses between blur-v1 strengths on the beat. The soundtrack is our track Show Me the Receipt, also made from quantum jobs, so the picture and the sound come from the same chain.

**Technical description**

> Frames rendered in Python with Pillow (make_video.py): five telablur-v1 morphs between successive ring stages, and blur-v1 at two strengths for the drop pulses. The frames are assembled with ffmpeg at 1280x720 and 24 fps, cut to the song's sections so the rings grow during the verse that describes the search. The engines ran on Qiskit Aer; the soundtrack's randomness came from comet-qrng-v1 on ibm_pittsburgh.

## Entry 8 of 10: #5 Quantum game

| Field | What to enter |
|---|---|
| Project title | Wear the Rings |
| Elevator pitch | A browser puzzle about an open maths problem: surround a tile with rings of copies of itself, then try to match the real record of 4 rings plus 251/254 of a fifth. |
| Challenge | Quantum game (#5) |
| Engines used | tessa-image-v1, comet-qrng-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session/tree/main/docs/game |
| Demo URL | https://kannaka-labs.github.io/ghost-signals-quantum-session/game/ (the record: add ?level=4&hint=1) |
| Non-Moth APIs | No |
| Poster art (upload) | output/demos/shots/game_l4_hint.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/demos/demo_game.mp4 |

**Project description**

> Wear the Rings is a puzzle about the Heesch problem. The task is to surround a tile with rings of copies of itself: no overlaps, every copy touching what is already built, and no trapped holes. Each ring is scored the way the open challenge scores it. Three plane-tiling shapes lead up to the real record holder, a 15-cell polyhex at 4 + 251/254. Pressing H ghosts in its record corona ring by ring, and the record replayed through the game's rules scores exactly 251/254 on ring 5. The quantum parts are real. Tessa textures every tile through a circuit under the ibm_fez noise model. In quantum-bag mode, each piece's orientation is dealt from 32 certified random bytes measured on IBM hardware. A run with strong entangling distortion on real hardware came back as pure noise, and we kept it as a result.

**Technical description**

> Vanilla JavaScript and canvas on GitHub Pages (docs/game), with exact hex-grid overlap, contact and hole checks plus ring scoring. tessa-image-v1 texture: colours mapped to Bloch-sphere points, read back through a circuit under the ibm_fez noise model, blended 45 percent over the originals. Quantum-bag orientations come from comet-qrng-v1 bytes measured on ibm_pittsburgh. The soundtrack is our track.

## Entry 9 of 10: #1 One image, one engine

| Field | What to enter |
|---|---|
| Project title | The Heesch leader, its frontier dissolved |
| Elevator pitch | One blur-v1 job, masked to the unsettled outer rings of a famous tiling record, so the proven rings stay sharp and the open frontier dissolves into interference. |
| Challenge | One image, one engine (#1) |
| Engines used | blur-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session |
| Demo URL | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/art/cover.png |
| Non-Moth APIs | No |
| Poster art (upload) | output/art/cover.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/demos/demo_one_image.mp4 |
| Additional images | output/art/stage_5.png (the source before the blur), output/art/mask_outer.png (the mask) |

**Project description**

> A single blur-v1 job applied to our render of the Heesch leader, the shape that holds the record for wearing rings of copies of itself (4 rings plus 251/254 of a fifth). A mask limits the quantum blur to rings 3 to 5, the part of the record that is still unsettled. The blur scatters those outer rings into interference echoes, while the proven inner rings stay sharp. The three cells the fifth ring could not cover glow red. The image is meant to read like the state of the problem itself: solid at the centre and dissolving at the frontier.

**Technical description**

> blur-v1 with strength 0.55, style rx, size 1024, and a mask (output/art/mask_outer.png) covering rings 3 to 5 only. The source is our own render of the leader's corona, drawn from its published cell coordinates (make_art.py). It is a single job, run on Qiskit Aer, with no post-processing beyond the mask. A stronger setting (0.85) is kept in the repo for comparison.

## Entry 10 of 10: #3 Three dimensions

| Field | What to enter |
|---|---|
| Project title | The Heesch leader as a ziggurat, shaded by the entanglement shader |
| Elevator pitch | A tiling record extruded into a stepped hex ziggurat, every face shaded with the entanglement shader's thin-film reflectance, so the colours travel as the camera orbits. |
| Challenge | Three dimensions (#3) |
| Engines used | entanglement-shader-v1 |
| Code repository | https://github.com/kannaka-labs/ghost-signals-quantum-session |
| Demo URL | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/shader/heesch_leader_entanglement_shader.mp4 |
| Non-Moth APIs | No |
| Poster art (upload) | output/shader/peek_11.png |
| Demo video | https://github.com/kannaka-labs/ghost-signals-quantum-session/blob/main/output/shader/heesch_leader_entanglement_shader.mp4 |

**Project description**

> A 20-second turntable of the Heesch leader extruded into hex prisms. Each ring sits one step lower than the one inside it, and the three cells the fifth ring could not cover are pits. Every face is shaded with the entanglement-shader-v1 reflectance lookup table, sampled at that face's own viewing angle. As the camera orbits, the thin-film colours travel across the walls. The soundtrack is the first drop of our track. We wanted the 3D piece to show the same object as the rest of the entry, so the record becomes something you can walk around, with its unsolved edge visible as a lower, broken step.

**Technical description**

> entanglement-shader-v1 (job b7f8ece2: layers 3, reflectance 0.2, absorption 0.95, style peaked) returns an RGBE reflectance lookup table. gsqs/render3d.py reads the table with a hand-written RGBE parser, ports the engine's GLSL lookup to Python, ray-casts the extruded prisms and samples the table per face and viewing angle, at a film thickness of 280 nm. Frames are assembled with ffmpeg.

## Held: #7 Make a VST or AU (Retrocausal Tap Delay)

The plugin is built and its DSP is unit-tested, but it has not been loaded in a DAW yet. Submit it only after you have loaded it in a host and re-rendered the examples. The entry text is in SUBMISSION-FORM.md.
