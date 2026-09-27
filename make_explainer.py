"""FQxI challenge (#11): "How do you know a random number is quantum?", a narrated explainer, ~90 s.

Every number on screen is from our own comet-qrng-v1 runs on 2026-09-27 (output/explainer/runs.json).
  python make_explainer.py <elevenlabs.key>
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import song, voice, visuals as v  # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "output" / "explainer"
OUT.mkdir(parents=True, exist_ok=True)
KEY = sys.argv[1]
W, H, FPS, SR = 1280, 720, 24, 44100
BG, INK, DIM, AMBER, TEAL, RED = v.BG, (236, 230, 216), (120, 140, 150), (216, 160, 72), (156, 195, 207), (255, 84, 60)
PULSE = json.loads((ROOT / "output" / "session-1" / "00_pulse.json").read_text())
HEX = PULSE["random"]["hex"]

RUNS = {  # from the three result files; h = conservative per-bit min-entropy (NIST SP 800-90B, 99%)
    "simulator (control)": {"S": 2.828, "sig": 0.022, "bits": 49152, "h": 0.903},
    "ibm_fez, 12 qubits": {"S": 2.609, "sig": 0.024, "bits": 49152, "h": 0.8677},
    "ibm_pittsburgh, 64 qubits": {"S": 2.696, "sig": 0.023, "bits": 262144, "h": 0.7918},
}
CHARGE = 43250          # bits: the price of counts-only readout (shot order is lost), 4096 shots
(OUT / "runs.json").write_text(json.dumps({"runs": RUNS, "ordering_charge_bits": CHARGE,
                                           "jobs": {"simulator": "0bfeb0b7-73d8-433c-9161-9fa66805f9b0",
                                                    "ibm_fez": "f1750798-cc50-4684-aa4c-c134a6bdac6c",
                                                    "ibm_pittsburgh": "2f709282-aa7e-42de-a506-814a92f789c8"}}, indent=1))

SCRIPT = [
    ("KANNAKA", "How do you know a random number is really quantum?", "title"),
    ("QE", "You can't tell by looking at it. Random looks the same from a coin, a computer, or a qubit. So we tested the machine instead.", "bytes"),
    ("QE", "First, a Bell test. Two entangled qubits, measured at different angles. Anything classical scores two at most. Quantum mechanics allows up to two point eight three.", "bell_axis"),
    ("KANNAKA", "And ours?", "bell_axis"),
    ("QE", "Two point seven, on IBM hardware. Thirty standard deviations past the classical limit. The device really is quantum.", "bell_runs"),
    ("KANNAKA", "So we can use every bit it gives us?", "bell_runs"),
    ("QE", "No. Noise means each raw bit carries less than a full bit of randomness. We measured about zero point eight. And the machine only reports how often each result came up, not in what order, so we pay for that lost order too: forty-three thousand bits.", "budget_explain"),
    ("QE", "With twelve qubits, the budget came up six hundred bits short. The engine gave us zero bytes. It refused to pretend.", "budget_12"),
    ("KANNAKA", "And with sixty-four?", "budget_12"),
    ("QE", "A hundred and sixty-four thousand bits to spare, and thirty-two certified bytes, with every assumption written down, including one we can't remove yet. Quantum randomness isn't a claim. It's a receipt.", "budget_64"),
]

F_BIG, F_MED, F_SM, F_MONO = v.font("bahnschrift.ttf", 60), v.font("segoeuisl.ttf", 36), v.font("segoeui.ttf", 26), v.font("consola.ttf", 30)


def canvas():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)


def ctext(d, y, s, f, fill):
    d.text(((W - d.textlength(s, font=f)) / 2, y), s, font=f, fill=fill)


def slide(kind, u):
    """u in [0,1]: progress through the slide, for simple build-ins."""
    im, d = canvas()
    if kind == "title":
        ctext(d, 250, "How do you know a random number", F_BIG, INK)
        ctext(d, 330, "is really quantum?", F_BIG, AMBER)
        ctext(d, 450, "three runs on the Moth Atlas comet-qrng-v1 engine, 27 Sept 2026", F_SM, DIM)
    elif kind == "bytes":
        shown = HEX[: max(2, int(len(HEX) * min(1, u * 1.5)))]
        rows = [shown[i:i + 32] for i in range(0, len(shown), 32)]
        for i, r in enumerate(rows):
            ctext(d, 250 + i * 48, " ".join(r[j:j + 2] for j in range(0, len(r), 2)), F_MONO, TEAL)
        ctext(d, 420, "32 bytes. Nothing in them says where they came from.", F_MED, INK)
    elif kind.startswith("bell"):
        x0, x1, y = 140, 1140, 320
        def X(s): return x0 + (s - 1.6) / (3.0 - 1.6) * (x1 - x0)
        d.line([(x0, y), (x1, y)], fill=DIM, width=3)
        for s in (1.6, 2.0, 2.4, 2.828, 3.0):
            d.line([(X(s), y - 8), (X(s), y + 8)], fill=DIM, width=2)
            lab = f"{s:.3g}"
            d.text((X(s) - d.textlength(lab, font=F_SM) / 2, y + 16), lab, font=F_SM, fill=DIM)
        d.rectangle([x0, y - 120, X(2.0), y - 4], fill=(40, 48, 56))
        d.text((x0 + 16, y - 110), "anything classical", font=F_SM, fill=INK)
        d.line([(X(2.828), y - 150), (X(2.828), y)], fill=AMBER, width=3)
        d.text((X(2.828) - 190, y - 185), "quantum maximum 2.828", font=F_SM, fill=AMBER)
        ctext(d, 80, "The Bell test: correlation score S", F_MED, INK)
        if kind == "bell_runs":
            for i, (name, r) in enumerate(RUNS.items()):
                yy = y + 80 + i * 56
                col = TEAL if "sim" in name else RED if "fez" in name else AMBER
                d.ellipse([X(r["S"]) - 9, yy - 9, X(r["S"]) + 9, yy + 9], fill=col)
                d.line([(X(r["S"] - 2 * r["sig"]), yy), (X(r["S"] + 2 * r["sig"]), yy)], fill=col, width=3)
                lab = f"{name}:  S = {r['S']:.3f} ± {r['sig']:.3f}"
                d.text((X(r["S"]) - d.textlength(lab, font=F_SM) - 40, yy - 16), lab, font=F_SM, fill=col)
    elif kind.startswith("budget"):
        ctext(d, 60, "The randomness budget", F_MED, INK)
        ctext(d, 110, "(raw bits × entropy per bit)  −  (the price of lost shot order)", F_SM, DIM)
        bars = []
        if kind in ("budget_explain", "budget_12"):
            r = RUNS["ibm_fez, 12 qubits"]
            bars = [("12 qubits on ibm_fez", r["bits"] * r["h"])]
        if kind == "budget_64":
            r = RUNS["ibm_pittsburgh, 64 qubits"]
            bars = [("12 qubits on ibm_fez", RUNS["ibm_fez, 12 qubits"]["bits"] * RUNS["ibm_fez, 12 qubits"]["h"]),
                    ("64 qubits on ibm_pittsburgh", r["bits"] * r["h"])]
        scale = 760 / 210000
        for i, (name, ent) in enumerate(bars):
            y0 = 220 + i * 215
            grow = min(1, u * 5) if kind != "budget_64" or i == 1 else 1
            d.text((180, y0 - 42), name, font=F_SM, fill=INK)
            d.rectangle([180, y0, 180 + ent * scale * grow, y0 + 56], fill=TEAL)
            d.rectangle([180, y0 + 70, 180 + CHARGE * scale, y0 + 110], fill=RED)
            d.text((180 + ent * scale * grow + 12, y0 + 12), f"{ent:,.0f} bits of entropy", font=F_SM, fill=TEAL)
            d.text((180 + CHARGE * scale + 12, y0 + 76), f"{CHARGE:,} bits charged", font=F_SM, fill=RED)
            left = ent - CHARGE
            if kind != "budget_explain" and grow >= 1:
                msg = f"short by {-left:,.0f} bits: 0 bytes certified" if left < 0 else f"{left:,.0f} bits spare: 32 bytes certified"
                d.text((180, y0 + 122), msg, font=F_SM, fill=RED if left < 0 else AMBER)
        if kind == "budget_64" and u > 0.5:
            ctext(d, 588, "assumption: no dependence between qubits beyond pairs (tested, not proven)", F_SM, DIM)
    return im


# narration: place lines back to back with a short breath, build the slide timeline from them
clips, t, timeline = [], 0.6, []
for who, text, kind in SCRIPT:
    x = voice.line(who, text, ROOT / "output" / "edm" / "vocals_cache", KEY)
    clips.append((t, x))
    timeline.append((t, t + len(x) / SR, kind, who, text))
    t += len(x) / SR + 0.45
T = t + 2.5
narr = np.zeros(int(T * SR))
for t0, x in clips:
    i = int(t0 * SR)
    narr[i:i + len(x)] += x / (np.abs(x).max() + 1e-9) * 0.8
bed = np.zeros(int(T * SR))            # a quiet Dm7 pad under the voices
for k in range(int(T / 4) + 1):
    p = song.pad_chord([62, 65, 69, 72], 4.0).mean(axis=1)
    i = int(k * 4 * SR)
    bed[i:i + len(p)] += p[: len(bed) - i]
bed = song.lowpass(bed, 1200) / (np.abs(bed).max() + 1e-9) * 0.12
song.write_wav(OUT / "explainer_audio.wav", np.stack([narr + bed] * 2, axis=1) * 0.95)

out = OUT / "how_do_you_know_a_random_number_is_quantum.mp4"
ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(OUT / "explainer_audio.wav"),
                       "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
F_SUB = v.font("segoeuisl.ttf", 28)
for f in range(int(T * FPS)):
    tt = f / FPS
    cur = next((seg for seg in timeline if seg[0] <= tt < seg[1] + 0.45), timeline[-1] if tt >= timeline[-1][0] else timeline[0])
    u = (tt - cur[0]) / max(cur[1] - cur[0], 1e-6)
    im = slide(cur[2], u) if tt < T - 2.5 else slide("title", 1)
    if tt >= T - 2.5:
        im, d = canvas()
        ctext(d, 300, "Quantum randomness isn't a claim. It's a receipt.", F_MED, AMBER)
        ctext(d, 380, "Kannaka Radio  ·  github.com/kannaka-labs/ghost-signals-quantum-session", F_SM, DIM)
    elif cur[0] <= tt < cur[1]:
        d = ImageDraw.Draw(im)
        who = "KANNAKA" if cur[3] == "KANNAKA" else "0xSCADA-QE"
        s = f"{who}:  {cur[4]}"
        words, lines_, line_ = s.split(), [], ""
        for w_ in words:
            if d.textlength(line_ + " " + w_, font=F_SUB) > W - 160:
                lines_.append(line_)
                line_ = w_
            else:
                line_ = (line_ + " " + w_).strip()
        lines_.append(line_)
        for i, ln in enumerate(lines_[-2:]):
            ctext(d, H - 92 + i * 36, ln, F_SUB, AMBER if cur[3] == "KANNAKA" else TEAL)
    ff.stdin.write(im.tobytes())
ff.stdin.close()
ff.wait()
print("wrote", out.name, f"{T:.1f} s")
