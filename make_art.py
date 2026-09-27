"""Quantum imagery for the cover (challenge #1) and the video (#4), all from the Heesch leader.

  python make_art.py <moth.key>

- cover: blur-v1 on the full corona, masked to rings 3-5 (the frontier), so only the unsettled edge
  scatters into interference echoes; the proven inner rings stay sharp.
- stages: the corona built ring by ring (0..5) at 1280x720; telablur-v1 morphs each stage into the next
  through a selector-qubit rotation, giving the in-between frames of the video.
- pulses: two blur strengths of the full stage for the drops.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gsqs import visuals as v  # noqa: E402
from gsqs.moth import Moth  # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "output" / "art"
OUT.mkdir(parents=True, exist_ok=True)
data = v.load(ROOT / "output" / "art" / "leader_figure.json")
m = Moth(key_file=sys.argv[1])
jobs = {}


def up(p):
    return m.upload(p, "image/png")


def run(name, engine, params, files, dest):
    if dest.exists():
        return
    j = m.run(engine, params, files)
    m.download(j, "result", dest)
    jobs[name] = {"engine": engine, "job_id": j["job_id"], "params": params}
    print(name, j["job_id"])


# cover
full = OUT / "corona_full.png"
v.render(data, (1400, 1400)).save(full)
v.mask_outer(data, (1400, 1400)).save(OUT / "mask_outer.png")
img_a, mask_a = up(full), up(OUT / "mask_outer.png")
for strength in (0.55, 0.85):
    run(f"cover_blur_{strength}", "blur-v1", {"strength": strength, "style": "rx", "size": 1024},
        {"image": img_a, "mask": mask_a}, OUT / f"cover_blur_{strength}.png")

# video stages, all framed like the full corona so they line up
size = (1280, 720)
s, c = v.frame(data, size)
for k in range(6):
    v.render(data, size, max_level=k, scale=s, center=c, glow=(k == 5)).save(OUT / f"stage_{k}.png")
v.mask_outer(data, size).save(OUT / "mask_outer_720.png")
stage_ids = [up(OUT / f"stage_{k}.png") for k in range(6)]
for k in range(5):
    run(f"morph_{k}_{k + 1}", "telablur-v1", {"strength": 0.5, "direction": "full", "size": 1024},
        {"image1": stage_ids[k], "image2": stage_ids[k + 1]}, OUT / f"morph_{k}_{k + 1}.png")
mask720 = up(OUT / "mask_outer_720.png")
for strength in (0.4, 0.8):
    run(f"pulse_{strength}", "blur-v1", {"strength": strength, "style": "rx", "size": 1024},
        {"image": stage_ids[5], "mask": mask720}, OUT / f"pulse_{strength}.png")

prov = OUT / "art_jobs.json"
old = json.loads(prov.read_text()) if prov.exists() else {}
prov.write_text(json.dumps({**old, **jobs}, indent=1))
print("done:", len(jobs), "new jobs")
