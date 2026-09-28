"""decode_model: score a stock SAT solver's model of an exported joint_multi CNF with the OFFICIAL verifier.

Independent of joint_multi's solve loop: it reads only
  - the exported DIMACS (to check that the model satisfies EVERY clause),
  - <cnf>.map.json (z-variable -> (level, placement) table written by the export hook),
  - the model (solver stdout with `v` lines, or a bare literal list),
then rebuilds the witness as a .heesch file and scores it through the official harness path
(heesch_verify.witness.verify_witness + heesch_verify.defect.verify_defect).

usage: python decode_model.py <cnf> <model-or-solver-stdout> [--out w.heesch]
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

from heesch_verify.defect import verify_defect
from heesch_verify.parse import DefectBlock, parse_submission
from heesch_verify.patch import check_corona, required_set
from heesch_verify.witness import VerifyConfig, verify_witness

sys.path.insert(0, str(Path(__file__).resolve().parent))


def read_model(p: Path) -> set[int]:
    lits = []
    for line in p.read_text().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "v":
            t = t[1:]
        elif not t[0].lstrip("-").isdigit():
            continue
        lits += [int(x) for x in t]
    return {x for x in lits if x != 0}


def check_cnf(cnf: Path, model: set[int]) -> tuple[int, int]:
    n = bad = 0
    with open(cnf, "rb") as fh:
        for line in fh:
            if line[:1] in (b"c", b"p") or not line.strip():
                continue
            cl = [int(x) for x in line.split()[:-1]]
            n += 1
            if not any(x in model for x in cl):
                bad += 1
                if bad <= 5:
                    print("  UNSATISFIED clause:", cl[:12], "..." if len(cl) > 12 else "")
    return n, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cnf", type=Path)
    ap.add_argument("model", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    meta = json.loads(Path(str(a.cnf) + ".map.json").read_text())
    model = read_model(a.model)
    n, bad = check_cnf(a.cnf, model)
    print(f"model satisfies {n - bad}/{n} clauses of {a.cnf.name}")
    if bad:
        print("MODEL DOES NOT SATISFY THE CNF")
        return 2

    text = Path(meta["submission"]).read_text(encoding="utf-8")
    sub = parse_submission(text)
    grid, shape = sub.grid, frozenset(sub.cells)
    from corona_opt import CONTACT_MODE
    contact = grid.contact(CONTACT_MODE)
    base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
    f, k = meta["free_from"], meta["k"]
    fixed_lines = [f"{lvl} {pl[1].as_text()}"
                   for pl, lvl in zip(sub.patches[0], base.levels) if lvl < f]
    chosen = [(lvl, xf) for v, (lvl, xf) in meta["z"].items() if int(v) in model]
    inner = [(l, xf) for l, xf in chosen if l <= k]
    partial = [(l, xf) for l, xf in chosen if l == k + 1]
    print(f"chosen tiles per level: " + str({l: sum(1 for x, _ in chosen if x == l) for l in range(f, k + 2)}))

    def render(dhc, dhh, req):
        body = [text.splitlines()[0], f"~ {k} {k} 1", str(len(fixed_lines) + len(inner))]
        body += fixed_lines + [f"{l} {xf}" for l, xf in inner]
        body += [f"#DEFECT {k + 1} {dhc} {dhh} {req}", str(len(partial))]
        body += [f"{l} {xf}" for l, xf in partial]
        return "\n".join(body) + "\n"

    # pass 1: loose ceilings to learn |R|; pass 2: exact claims through the official harness path
    big = 10**6
    for attempt in range(2):
        try:
            outc = verify_witness(render(big, big, 0) if attempt == 0 else render(dhc, dhh, req), VerifyConfig())
        except Exception as e:  # noqa: BLE001
            print(f"OFFICIAL verify_witness REJECTS the decoded configuration: {e}")
            return 3
        s2 = outc.submission
        if attempt == 0:
            req = len(required_set(outc.hc_corona.patch_cells, outc.contact))
            s2 = parse_submission(render(big, big, req))
        res = verify_defect(frozenset(s2.cells), s2.grid, outc.hc_corona, s2.defect, outc.contact,
                            allow_reflections=VerifyConfig().allow_reflections)
        dhc, dhh = res.defect_hc, res.defect_hh
    score = outc.result.hc_verified + Fraction(res.required - res.defect_hc, res.required)
    print(f"OFFICIAL: hc_verified={outc.result.hc_verified} defect_hc={res.defect_hc} (hh={res.defect_hh}, "
          f"pockets={res.pocket_cells}) of |R|={res.required} -> score {float(score):.6f} ({score})")
    print(f"claim bound in CNF: defect <= {meta['U']}, |R| >= {meta['RMIN']} -> "
          f"{'CONSISTENT' if res.defect_hc <= meta['U'] and res.required >= meta['RMIN'] else 'VIOLATED'}")
    if a.out:
        a.out.write_text(render(dhc, dhh, res.required), encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
