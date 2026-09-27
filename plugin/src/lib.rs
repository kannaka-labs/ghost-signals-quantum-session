//! Retrocausal Tap Delay: a VST3/CLAP plugin whose delay taps were measured on a quantum computer.
//!
//! The tap maps come from Moth Atlas `retrocausal-echo-v1` with `emit: "map"`: the engine scrambles a
//! qubit chain, kicks one site, runs the circuit backward, and reports the signed return at each site
//! and depth as a tap (time, level, pan, polarity). This plugin plays those taps in sync with the host
//! tempo. Presets are three measured maps (see maps.rs for their job ids).

use nih_plug::prelude::*;
use std::sync::Arc;

pub mod dsp;
pub mod maps;

#[derive(Enum, PartialEq, Clone, Copy)]
pub enum MapChoice {
    #[name = "Receipt room (chain, 8 sites)"]
    ReceiptRoom,
    #[name = "Square lattice 5x4"]
    Square,
    #[name = "Disordered chain"]
    Disordered,
}

#[derive(Params)]
pub struct RetroParams {
    #[id = "map"]
    pub map: EnumParam<MapChoice>,
    #[id = "mix"]
    pub mix: FloatParam,
    #[id = "feedback"]
    pub feedback: FloatParam,
    #[id = "stretch"]
    pub stretch: FloatParam,
    #[id = "width"]
    pub width: FloatParam,
    #[id = "polarity"]
    pub keep_polarity: BoolParam,
}

impl Default for RetroParams {
    fn default() -> Self {
        Self {
            map: EnumParam::new("Measured map", MapChoice::ReceiptRoom),
            mix: FloatParam::new("Mix", 0.45, FloatRange::Linear { min: 0.0, max: 1.0 })
                .with_smoother(SmoothingStyle::Linear(30.0))
                .with_unit(" %")
                .with_value_to_string(formatters::v2s_f32_percentage(0))
                .with_string_to_value(formatters::s2v_f32_percentage()),
            feedback: FloatParam::new("Feedback", 0.25, FloatRange::Linear { min: 0.0, max: 0.9 })
                .with_smoother(SmoothingStyle::Linear(30.0))
                .with_unit(" %")
                .with_value_to_string(formatters::v2s_f32_percentage(0))
                .with_string_to_value(formatters::s2v_f32_percentage()),
            stretch: FloatParam::new("Time stretch", 1.0, FloatRange::Skewed { min: 0.5, max: 2.0, factor: FloatRange::skew_factor(-1.0) })
                .with_smoother(SmoothingStyle::Linear(60.0))
                .with_unit(" x"),
            width: FloatParam::new("Stereo width", 1.0, FloatRange::Linear { min: 0.0, max: 1.5 })
                .with_smoother(SmoothingStyle::Linear(30.0)),
            keep_polarity: BoolParam::new("Keep inversions", true),
        }
    }
}

pub struct RetroTap {
    params: Arc<RetroParams>,
    delay: dsp::TapDelay,
}

impl Default for RetroTap {
    fn default() -> Self {
        Self { params: Arc::new(RetroParams::default()), delay: dsp::TapDelay::new() }
    }
}

impl Plugin for RetroTap {
    const NAME: &'static str = "Retrocausal Tap Delay";
    const VENDOR: &'static str = "Kannaka Radio";
    const URL: &'static str = "https://github.com/kannaka-labs/ghost-signals-quantum-session";
    const EMAIL: &'static str = "radio@kannaka.invalid";
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");

    const AUDIO_IO_LAYOUTS: &'static [AudioIOLayout] = &[AudioIOLayout {
        main_input_channels: NonZeroU32::new(2),
        main_output_channels: NonZeroU32::new(2),
        ..AudioIOLayout::const_default()
    }];
    const MIDI_INPUT: MidiConfig = MidiConfig::None;
    const SAMPLE_ACCURATE_AUTOMATION: bool = false;

    type SysExMessage = ();
    type BackgroundTask = ();

    fn params(&self) -> Arc<dyn Params> {
        self.params.clone()
    }

    fn initialize(&mut self, _layout: &AudioIOLayout, config: &BufferConfig, _ctx: &mut impl InitContext<Self>) -> bool {
        self.delay.prepare(config.sample_rate);
        true
    }

    fn reset(&mut self) {
        self.delay.clear();
    }

    fn process(&mut self, buffer: &mut Buffer, _aux: &mut AuxiliaryBuffers, context: &mut impl ProcessContext<Self>) -> ProcessStatus {
        let bpm = context.transport().tempo.unwrap_or(120.0) as f32;
        let taps = maps::MAPS[self.params.map.value().to_index()].taps;
        let keep = self.params.keep_polarity.value();
        let wet_gain = dsp::wet_norm(taps, self.params.width.value(), keep);
        for mut frame in buffer.iter_samples() {
            let s = dsp::Settings {
                bpm,
                stretch: self.params.stretch.smoothed.next(),
                mix: self.params.mix.smoothed.next(),
                feedback: self.params.feedback.smoothed.next(),
                width: self.params.width.smoothed.next(),
                keep_polarity: keep,
                wet_gain,
            };
            let mut it = frame.iter_mut();
            let (l, r) = (it.next().unwrap(), it.next().unwrap());
            let (ol, or) = self.delay.tick(*l, *r, taps, &s);
            *l = ol;
            *r = or;
        }
        ProcessStatus::Normal
    }
}

impl ClapPlugin for RetroTap {
    const CLAP_ID: &'static str = "radio.kannaka.retrocausal-tap-delay";
    const CLAP_DESCRIPTION: Option<&'static str> = Some("Multi-tap delay with taps measured on a quantum computer");
    const CLAP_MANUAL_URL: Option<&'static str> = Some(Self::URL);
    const CLAP_SUPPORT_URL: Option<&'static str> = None;
    const CLAP_FEATURES: &'static [ClapFeature] = &[ClapFeature::AudioEffect, ClapFeature::Delay, ClapFeature::Stereo];
}

impl Vst3Plugin for RetroTap {
    const VST3_CLASS_ID: [u8; 16] = *b"KannakaRetroTap1";
    const VST3_SUBCATEGORIES: &'static [Vst3SubCategory] = &[Vst3SubCategory::Fx, Vst3SubCategory::Delay];
}

nih_export_clap!(RetroTap);
nih_export_vst3!(RetroTap);
