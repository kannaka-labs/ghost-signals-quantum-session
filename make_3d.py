"""Challenge #3 (Three dimensions): the Heesch leader as a 3D ziggurat, shaded with entanglement-shader-v1.

A 20 s turntable. Every face samples the engine's reflectance LUT at its own viewing angle, via a port
of the engine's GLSL (gsqs/render3d.py), so the thin-film colours travel across the walls as the camera
orbits. Soundtrack: the first drop of "Show Me the Receipt".
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import render3d as r3, song, visuals as v  # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "output" / "shader"
W, H, FPS, SECONDS = 1280, 720, 24, 20
job = json.loads((OUT / "shader_job.json").read_text())
cells = r3.build(v.load(ROOT / "output" / "art" / "leader_figure.json"), ring_height=4.5, base=24.0)
shader = r3.Shader(OUT / "R_lut.hdr", thickness=280)

# soundtrack: 20 s from the first drop, faded
edm = json.loads((ROOT / "output" / "edm" / "edm_provenance.json").read_text())
t0 = next(s["start_s"] for s in edm["form"] if s["name"] == "drop")
x = song.read_wav(ROOT / "output" / "edm" / "show_me_the_receipt.wav")
seg = x[int(t0 * 44100): int((t0 + SECONDS) * 44100)].copy()
f = int(1.5 * 44100)
seg[:f] *= np.linspace(0, 1, f)[:, None]
seg[-f:] *= np.linspace(1, 0, f)[:, None]
song.write_wav(OUT / "turntable_audio.wav", seg)

F1, F2 = v.font("bahnschrift.ttf", 40), v.font("consola.ttf", 22)
out = OUT / "heesch_leader_entanglement_shader.mp4"
ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo",
                       "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", str(OUT / "turntable_audio.wav"), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(out)],
                      stdin=subprocess.PIPE)
n = SECONDS * FPS
for i in range(n):
    u = i / n
    im = r3.render(cells, shader, yaw=0.6 + 2 * math.pi * u, pitch=0.5 + 0.1 * math.sin(2 * math.pi * u),
                   zoom=1.9 + 0.15 * math.sin(math.pi * u), size=(W, H))
    d = ImageDraw.Draw(im)
    a = min(1.0, max(0.0, 3.5 - abs(u - 0.12) * 18)) if u < 0.3 else 0.0
    if a > 0:
        c = tuple(int(k * a) for k in (236, 230, 216))
        d.text((60, 50), "The Heesch leader, in three dimensions", font=F1, fill=c)
        d.text((60, 104), f"shaded by entanglement-shader-v1  (job {job['job_id'][:8]}, layers {job['params']['layers']}, "
                          f"style {job['params']['style']})", font=F2, fill=tuple(int(k * a) for k in (156, 195, 207)))
    d.text((60, H - 50), "4 rings + 251/254 of a fifth  ·  the three pits are the cells no copy could cover",
           font=F2, fill=(120, 140, 150))
    ff.stdin.write(im.tobytes())
    if i % (FPS * 5) == 0:
        print(f"{i / FPS:5.1f}s", flush=True)
ff.stdin.close()
ff.wait()
print("wrote", out.name)
