"""Music video for "Show Me the Receipt" (challenge #4), 1280x720 at 24 fps.

Keyframes: the Heesch leader built ring by ring (local renders), telablur-v1 morphs between successive
rings, and blur-v1 pulses for the drops (quantum jobs in output/art/art_jobs.json). The picture follows
the lyric: the verse grows the rings while it describes the search, the build zooms toward the three
bare cells, the drops pulse between blur strengths on the beat. Lyrics are subtitled in speaker colour.
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import edm, visuals as v  # noqa: E402

ROOT = Path(__file__).parent
ART, EDM = ROOT / "output" / "art", ROOT / "output" / "edm"
W, H, FPS = 1280, 720, 24
card = json.loads((EDM / "edm_provenance.json").read_text())
starts = {s["name"]: s["start_s"] for s in card["form"]}
audio = EDM / "show_me_the_receipt.wav"
T = card["length_s"]


def load(name):
    return np.asarray(Image.open(ART / name).convert("RGB").resize((W, H), Image.LANCZOS), dtype=np.float32)


stage = [load(f"stage_{k}.png") for k in range(6)]
morph = [load(f"morph_{k}_{k + 1}.png") for k in range(5)]
pulse = {0.4: load("pulse_0.4.png"), 0.8: load("pulse_0.8.png")}
cover = np.asarray(Image.open(ART / "cover.png").convert("RGB").resize((H, H), Image.LANCZOS), dtype=np.float32)
cover_frame = np.zeros((H, W, 3), np.float32) + np.array(v.BG, np.float32)
cover_frame[:, (W - H) // 2:(W - H) // 2 + H] = cover

# the growth path: stage k -> morph k,k+1 -> stage k+1 ...
path = []
for k in range(5):
    path += [stage[k], morph[k]]
path.append(stage[5])


def along(images, u):
    """Crossfade along a list of keyframes, u in [0,1]."""
    x = np.clip(u, 0, 1) * (len(images) - 1)
    i = min(int(x), len(images) - 2)
    f = x - i
    f = f * f * (3 - 2 * f)
    return images[i] * (1 - f) + images[i + 1] * f


def zoom(img, z, cx=0.5, cy=0.5, shake=0.0):
    if z <= 1.0001 and not shake:
        return img
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    w, h = W / z, H / z
    x0 = np.clip(cx * W - w / 2 + shake, 0, W - w)
    y0 = np.clip(cy * H - h / 2, 0, H - h)
    return np.asarray(im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)), dtype=np.float32)


def beat_env(t, t0):
    """Pulse envelope in a drop: every beat, harder on the downbeat and on the half-time snare (beat 3)."""
    b = (t - t0) / edm.BEAT
    phase, k = b % 1.0, int(b) % 4
    weight = 1.0 if k == 0 else (0.8 if k == 2 else 0.4)
    return weight * np.exp(-phase * 5)


# the bare cell nearest the left edge is where the build zooms
bare_left = (230 / 1400, 815 / 1400)

raw_lines = card["vocals"]["lines"]
lines = []
for i, ln in enumerate(raw_lines):
    nxt = raw_lines[i + 1]["t"] if i + 1 < len(raw_lines) else T
    end = min(nxt - 0.1, ln["t"] + 1.0 + 0.068 * len(ln["text"]))
    # long lines (the hook) become their phrases, each on screen for its share of the time
    parts = [p.strip() for p in ln["text"].replace(". ", ".|").split("|") if p.strip()]
    total = sum(len(p) for p in parts)
    t0 = ln["t"]
    for p in parts:
        dt = (end - ln["t"]) * len(p) / total
        lines.append({"t": t0, "end": t0 + dt, "text": p, "who": ln["who"]})
        t0 += dt
FONT = v.font("segoeuisl.ttf", 34)
COL = {"KANNAKA": (236, 190, 110), "QE": (170, 214, 226)}


def frame_at(t):
    s = starts
    if t < s["verse"]:
        u = t / s["verse"]
        img = stage[0] * min(1, t / 3) + np.array(v.BG, np.float32) * (1 - min(1, t / 3))
        img = zoom(img, 1.0 + 0.25 * (1 - u))
    elif t < s["build"]:
        img = along(path[:8], (t - s["verse"]) / (s["build"] - s["verse"]))
    elif t < s["drop"]:
        u = (t - s["build"]) / (s["drop"] - s["build"])
        img = along(path[7:], min(1, u * 1.6))
        img = zoom(img, 1 + 1.6 * u ** 2, *bare_left)
        if u > 0.97:
            img = img + (u - 0.97) / 0.03 * 255
    elif t < s["break"] or s["drop2"] <= t < s["outro"]:
        t0 = s["drop"] if t < s["break"] else s["drop2"]
        e = beat_env(t, t0)
        img = stage[5] * (1 - e) + pulse[0.8 if t0 == s["drop2"] else 0.4] * e
        img = zoom(img, 1.0 + 0.04 * e, shake=6 * e * np.sin(t * 40))
    elif t < s["build2"]:
        u = (t - s["break"]) / (s["build2"] - s["break"])
        img = pulse[0.8] * (1 - u) + stage[5] * u
        img = zoom(img, 1.12 - 0.1 * u, 0.5 + 0.05 * np.sin(u * 3), 0.5)
    elif t < s["drop2"]:
        u = (t - s["build2"]) / (s["drop2"] - s["build2"])
        img = along(path, (u * 1.4) % 1.0)          # the whole search replayed, faster, as the bridge speaks
        img = zoom(img, 1 + 0.5 * u)
    else:
        u = (t - s["outro"]) / max(T - s["outro"], 1e-6)
        img = stage[5] * (1 - min(1, u * 2)) + cover_frame * min(1, u * 2)
        if u > 0.85:
            img = img * (1 - (u - 0.85) / 0.15)
    return img


def subtitle(im, t):
    for ln in lines:
        if ln["t"] <= t < ln["end"]:
            d = ImageDraw.Draw(im)
            w = d.textlength(ln["text"], font=FONT)
            x, y = (W - w) / 2, H - 78
            d.rounded_rectangle([x - 18, y - 8, x + w + 18, y + 46], 10, fill=(8, 13, 19))
            d.text((x, y), ln["text"], font=FONT, fill=COL[ln["who"]])
    return im


out = ROOT / "output" / "video" / "show_me_the_receipt.mp4"
out.parent.mkdir(parents=True, exist_ok=True)
ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)],
                      stdin=subprocess.PIPE)
n = int(T * FPS)
for f in range(n):
    t = f / FPS
    img = frame_at(t)
    # floor near-black to the background: removes the faint tiling blocks telablur leaves in empty space
    dark = img.max(axis=2) < 34
    img[dark] = v.BG
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    ff.stdin.write(subtitle(im, t).tobytes())
    if f % (FPS * 20) == 0:
        print(f"{t:6.1f}s", flush=True)
ff.stdin.close()
ff.wait()
print("wrote", out, round(out.stat().st_size / 1e6, 1), "MB")
