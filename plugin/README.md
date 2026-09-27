# Retrocausal Tap Delay (VST3 · CLAP)

A tempo-synced multi-tap delay whose taps were **measured on a quantum computer**. Moth Hack 2026, challenge #7.

The Moth Atlas engine `retrocausal-echo-v1` takes a chain (or lattice) of qubits, scrambles it, kicks one
site, and runs the circuit backward. The signed return it measures at each site and depth becomes one
delay tap: a time, a level, a pan, and a polarity. A **negative return comes back phase-inverted**. With
`emit: "map"` the engine returns only that tap map, "so a sequencer or plugin can place the events
itself". This is that plugin.

| preset | measured by | taps | inverted |
|---|---|---|---|
| Receipt room (chain, 8 sites) | job `f103da4a…`: the echo on the song *Show Me the Receipt* | 51 | 37 |
| Square lattice 5×4 | job `d8ad2243…`, `lattice square, 5×4, depth 6, theta_z 0.6` | 70 | 7 |
| Disordered chain | job `ce972e74…`, `chain, 8 sites, depth 6, disorder 0.45` | 37 | 18 |

Tap times are stored in sixteenth notes, so the delay follows the host tempo.

**Controls:**
- Measured map
- Mix
- Feedback (soft-saturated)
- Time stretch (0.5–2×)
- Stereo width
- Keep inversions: turn it off to hear the same map with every tap positive.

## Install (Windows x64)

Unzip `RetrocausalTapDelay-win64.zip`, then:
- copy `Retrocausal Tap Delay.vst3` (a folder) to `C:\Program Files\Common Files\VST3\`;
- or copy `Retrocausal Tap Delay.clap` to `C:\Program Files\Common Files\CLAP\`.

## Audio examples

These are rendered with the plugin's own DSP (`src/dsp.rs`, the same code the plugin runs) by
`cargo run --release --bin render_examples`. Settings: mix 50%, feedback 30%, all inversions kept.

- `examples/in_hook_vocal_140bpm.wav` is the dry hook of the song. It is rendered through all three
  maps as `hook_vocal_0_receipt`, `hook_vocal_1_square` and `hook_vocal_2_disordered`.
- `examples/in_melody_84bpm.wav` is the quantum-reservoir melody. It is rendered as `melody_0/1/2_*.wav`.

## One thing we measured while building it

Taps from different sites at the same depth arrive at the same instant, and with opposite polarities
they **cancel**. Normalising the wet bus by tap count left the echo at 2–5% of the output energy. The
plugin instead normalises by the map's *net* response per tap time (`dsp::wet_norm`), which brings the
surviving echo up to 34–60% of the output at 50% mix. The cancellation stays in the sound; it is part
of what the map measured.

## Build

```
cargo test --release --lib          # tap timing and polarity tests
cargo build --release               # target/release/retrocausal_tap_delay.dll exports VST3 + CLAP
python gen_maps.py                  # regenerate src/maps.rs from the engine's tap-map JSON
```

Checked: the DLL exports `GetPluginFactory`/`InitDll`/`ExitDll` (VST3) and `clap_entry` (CLAP).
Not yet tested inside a DAW on this machine.

Licence: GPL-3.0-or-later (nih-plug's VST3 bindings are GPLv3). Built with
[nih-plug](https://github.com/robbert-vdh/nih-plug).
