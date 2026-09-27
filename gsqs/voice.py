"""Vocal lines via ElevenLabs text-to-speech, cached per (voice, settings, text) so a line is paid for once.

Cast (Kannaka Radio's standing voices):
  KANNAKA     NTqGiNK8P02i66yY2GOH  the station
  0xSCADA-QE  cjVigY5qzO86Huf0OWal  the measurement engineer; highest stability, lowest style on purpose
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import requests

CAST = {
    "KANNAKA": {"voice_id": "NTqGiNK8P02i66yY2GOH",
                "settings": {"stability": 0.42, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}},
    "QE": {"voice_id": "cjVigY5qzO86Huf0OWal",
           "settings": {"stability": 0.82, "similarity_boost": 0.75, "style": 0.03, "use_speaker_boost": True}},
}
MODEL = "eleven_multilingual_v2"
SR = 44100


def _key(key_file=None):
    k = os.environ.get("ELEVENLABS_API_KEY")
    if not k and key_file:
        k = Path(key_file).read_text(encoding="utf-8").strip()
        k = k.split("=", 1)[1].strip() if "=" in k else k
    if not k:
        raise RuntimeError("set ELEVENLABS_API_KEY or pass key_file")
    return k


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Band-limited FFT resampling (pcm_44100 is Pro-tier only; 24 kHz carries speech fully)."""
    n_out = int(round(len(x) * sr_out / sr_in))
    X = np.fft.rfft(x)
    Y = np.zeros(n_out // 2 + 1, dtype=complex)
    k = min(len(X), len(Y))
    Y[:k] = X[:k]
    return np.fft.irfft(Y, n_out) * (n_out / len(x))


def line(who: str, text: str, cache: Path, key_file=None) -> np.ndarray:
    """Mono float array at 44.1 kHz for one spoken line."""
    c = CAST[who]
    h = hashlib.sha256(json.dumps([c, MODEL, text], sort_keys=True).encode()).hexdigest()[:20]
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{who}_{h}.pcm24"
    if not f.exists():
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{c['voice_id']}?output_format=pcm_24000",
            headers={"xi-api-key": _key(key_file), "accept": "audio/pcm"},
            json={"text": text, "model_id": MODEL, "voice_settings": c["settings"]}, timeout=120)
        if not r.ok:
            raise RuntimeError(f"ElevenLabs HTTP {r.status_code}: {r.text[:300]}")
        f.write_bytes(r.content)
        (cache / f"{who}_{h}.txt").write_text(text, encoding="utf-8")
    x = resample(np.frombuffer(f.read_bytes(), "<i2").astype(float) / 32768, 24000, SR)
    # trim leading/trailing near-silence so placement lands on the first syllable
    nz = np.flatnonzero(np.abs(x) > 0.01)
    return x[max(nz[0] - 200, 0): nz[-1] + 2000] if len(nz) else x
