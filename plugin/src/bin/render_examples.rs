//! Render the audio examples for the plugin submission with the plugin's own DSP (no host needed):
//!   cargo run --release --bin render_examples -- <input.wav> <bpm> <out_prefix>
//! Writes one WAV per measured map.

use retrocausal_tap_delay::{dsp, maps};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (input, bpm, prefix) = (&args[1], args[2].parse::<f32>().unwrap(), &args[3]);
    let mut reader = hound::WavReader::open(input).expect("input wav");
    let spec = reader.spec();
    let ch = spec.channels as usize;
    let samples: Vec<f32> = match spec.sample_format {
        hound::SampleFormat::Int => reader.samples::<i32>().map(|s| s.unwrap() as f32 / (1 << (spec.bits_per_sample - 1)) as f32).collect(),
        hound::SampleFormat::Float => reader.samples::<f32>().map(|s| s.unwrap()).collect(),
    };
    let frames = samples.len() / ch;
    let tail = (spec.sample_rate as f32 * 3.0) as usize;
    for (k, map) in maps::MAPS.iter().enumerate() {
        let mut d = dsp::TapDelay::new();
        d.prepare(spec.sample_rate as f32);
        let s = dsp::Settings { bpm, stretch: 1.0, mix: 0.5, feedback: 0.3, width: 1.0, keep_polarity: true,
                                wet_gain: dsp::wet_norm(map.taps, 1.0, true) };
        let out_spec = hound::WavSpec { channels: 2, sample_rate: spec.sample_rate, bits_per_sample: 16, sample_format: hound::SampleFormat::Int };
        let path = format!("{prefix}_{k}_{}.wav", map.name.split(' ').next().unwrap().to_lowercase());
        let mut w = hound::WavWriter::create(&path, out_spec).unwrap();
        let mut peak = 0.0f32;
        let mut buf = Vec::with_capacity((frames + tail) * 2);
        for i in 0..frames + tail {
            let (l, r) = if i < frames {
                let l = samples[i * ch];
                (l, if ch > 1 { samples[i * ch + 1] } else { l })
            } else {
                (0.0, 0.0)
            };
            let (ol, or) = d.tick(l, r, map.taps, &s);
            peak = peak.max(ol.abs()).max(or.abs());
            buf.push(ol);
            buf.push(or);
        }
        let g = if peak > 0.0 { 0.89 / peak } else { 1.0 };
        for v in buf {
            w.write_sample((v * g * 32767.0) as i16).unwrap();
        }
        w.finalize().unwrap();
        println!("{path}  ({}, job {})", map.name, map.job);
    }
}
