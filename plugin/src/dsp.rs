//! The delay itself, independent of any plugin API, so the plugin and the offline example renderer run
//! exactly the same code.
//!
//! Each tap is (time in sixteenth notes, level, pan, polarity), read from a retrocausal-echo-v1 tap map:
//! the engine kicks one site of a scrambled qubit chain, runs it backward, and turns the signed return
//! at each site and depth into a delay tap. A negative return comes back phase-inverted.

pub type Tap = (f32, f32, f32, f32);

pub struct TapDelay {
    sr: f32,
    buf: Vec<f32>,
    w: usize,
}

/// Wet-bus gain that brings a map's NET response to unity. Taps from different sites at the same depth
/// land at the same instant, and with opposite polarities they cancel; normalising by tap count would
/// leave the surviving echo nearly silent. Group by time, sum the panned signed levels, and invert the
/// resulting energy.
pub fn wet_norm(taps: &[Tap], width: f32, keep_polarity: bool) -> f32 {
    let mut groups: Vec<(f32, f32, f32)> = Vec::new();
    for &(steps, level, pan, polarity) in taps {
        let g = level * if keep_polarity { polarity } else { 1.0 };
        let p = (pan * width).clamp(-1.0, 1.0);
        let (gl, gr) = (g * ((1.0 - p) * 0.5).sqrt(), g * ((1.0 + p) * 0.5).sqrt());
        match groups.iter_mut().find(|(t, _, _)| (t - steps).abs() < 1e-3) {
            Some(e) => {
                e.1 += gl;
                e.2 += gr;
            }
            None => groups.push((steps, gl, gr)),
        }
    }
    let energy: f32 = groups.iter().map(|(_, l, r)| (l * l + r * r) * 0.5).sum();
    if energy > 1e-9 { 1.0 / energy.sqrt() } else { 1.0 }
}

pub struct Settings {
    pub bpm: f32,
    pub stretch: f32,
    pub mix: f32,
    pub feedback: f32,
    pub width: f32,
    pub keep_polarity: bool,
    /// from `wet_norm` for the current map and settings
    pub wet_gain: f32,
}

impl Default for TapDelay {
    fn default() -> Self {
        Self::new()
    }
}

impl TapDelay {
    pub fn new() -> Self {
        Self { sr: 44100.0, buf: vec![0.0; 1], w: 0 }
    }

    /// Room for the longest tap: 8 sixteenths at 30 bpm with a 2x stretch is 8 s.
    pub fn prepare(&mut self, sample_rate: f32) {
        self.sr = sample_rate;
        self.buf = vec![0.0; (sample_rate * 8.5) as usize + 4];
        self.w = 0;
    }

    pub fn clear(&mut self) {
        self.buf.iter_mut().for_each(|x| *x = 0.0);
    }

    #[inline]
    fn read(&self, delay_samples: f32) -> f32 {
        let n = self.buf.len();
        let pos = self.w as f32 - delay_samples;
        let pos = if pos < 0.0 { pos + n as f32 } else { pos };
        let i = pos.floor() as usize % n;
        let j = (i + 1) % n;
        let f = pos - pos.floor();
        self.buf[i] * (1.0 - f) + self.buf[j] * f
    }

    /// One stereo sample in, one out. The taps read a mono sum and place their own stereo image,
    /// as the engine does.
    #[inline]
    pub fn tick(&mut self, l: f32, r: f32, taps: &[Tap], s: &Settings) -> (f32, f32) {
        let sixteenth = 60.0 / s.bpm.max(30.0) / 4.0 * s.stretch * self.sr;
        let (mut wl, mut wr) = (0.0f32, 0.0f32);
        for &(steps, level, pan, polarity) in taps {
            let x = self.read(steps * sixteenth);
            let g = level * if s.keep_polarity { polarity } else { 1.0 };
            let p = (pan * s.width).clamp(-1.0, 1.0);
            wl += g * x * ((1.0 - p) * 0.5).sqrt();
            wr += g * x * ((1.0 + p) * 0.5).sqrt();
        }
        wl *= s.wet_gain;
        wr *= s.wet_gain;
        let fb = (s.feedback * 0.5 * (wl + wr)).tanh();
        self.buf[self.w] = 0.5 * (l + r) + fb;
        self.w = (self.w + 1) % self.buf.len();
        (l * (1.0 - s.mix) + wl * s.mix, r * (1.0 - s.mix) + wr * s.mix)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn settings(keep: bool) -> Settings {
        Settings { bpm: 120.0, stretch: 1.0, mix: 1.0, feedback: 0.0, width: 1.0, keep_polarity: keep, wet_gain: 1.0 }
    }

    #[test]
    fn a_single_tap_lands_at_its_time_with_its_polarity() {
        let mut d = TapDelay::new();
        d.prepare(1000.0);
        // one sixteenth at 120 bpm = 125 ms = 125 samples at 1 kHz; centre pan; inverted
        let taps = [(1.0, 1.0, 0.0, -1.0)];
        let mut out = vec![];
        for i in 0..300 {
            let x = if i == 0 { 1.0 } else { 0.0 };
            out.push(d.tick(x, x, &taps, &settings(true)).0);
        }
        let peak = (0..300).max_by(|&a, &b| out[a].abs().partial_cmp(&out[b].abs()).unwrap()).unwrap();
        assert_eq!(peak, 125);
        assert!(out[125] < 0.0, "an inverted tap must come back phase-flipped");
        let mut d2 = TapDelay::new();
        d2.prepare(1000.0);
        let first = d2.tick(1.0, 1.0, &taps, &settings(false)).0;
        let mut v = first;
        for _ in 1..=125 {
            v = d2.tick(0.0, 0.0, &taps, &settings(false)).0;
        }
        assert!(v > 0.0, "with polarity ignored the same tap is positive");
    }

    #[test]
    fn dry_passes_untouched_at_zero_mix() {
        let mut d = TapDelay::new();
        d.prepare(48000.0);
        let s = Settings { mix: 0.0, ..settings(true) };
        assert_eq!(d.tick(0.3, -0.2, &[(1.0, 1.0, 0.0, 1.0)], &s), (0.3, -0.2));
    }
}
