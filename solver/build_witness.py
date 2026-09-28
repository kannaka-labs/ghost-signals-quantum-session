"""build_witness: a hole-free k-corona witness for any shape, from the official encoder.

Encodes F(S, m) with heesch_encoder.multilevel (the frozen encoder the proof
pipeline uses; a hole-permitted relaxation), solves it, decodes the model with
the encoder's own decode_model + config_to_corona_placements, and checks it with
the verifier's check_corona(hole_mode="hc"). A model with an enclosed empty
region H gets the sound lazy cut
    (OR every level's placements covering H) v (OR -chosen placements bordering H)
and is re-solved, until a hole-free witness appears or the formula is UNSAT
(then no hole-free m-corona exists: Hc < m).

usage: python build_witness.py --grid H --cells "x,y x,y ..." --m 4 --out shape.heesch
       python build_witness.py --kaplan hex11-kaplan-hc4hh4 --m 4 --out hex11.heesch
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corona_opt import CONTACT_MODE  # noqa: E402

from heesch_encoder.multilevel.clauses import build_ml_formula  # noqa: E402
from heesch_encoder.multilevel.model import config_to_corona_placements, decode_model  # noqa: E402
from heesch_verify.grids import HexGrid, SquareGrid, TriGrid  # noqa: E402
from heesch_verify.patch import check_corona  # noqa: E402
from heesch_verify.result import VerifyError  # noqa: E402
from heesch_verify.shape import holes_of  # noqa: E402
from pysat.solvers import Solver  # noqa: E402

GRIDS = {"H": HexGrid, "O": SquareGrid, "I": TriGrid}


def kaplan(name):
    sys.path.insert(0, str(Path.cwd() / "tools"))
    from ml_feasibility import KAPLAN_SHAPES
    g, cells = KAPLAN_SHAPES[name]
    return g, cells


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grid", choices=sorted(GRIDS))
    ap.add_argument("--cells", help='"x,y x,y ..."')
    ap.add_argument("--kaplan", help="a KAPLAN_SHAPES key from tools/ml_feasibility.py (run from the heesch repo)")
    ap.add_argument("--m", type=int, default=4)
    ap.add_argument("--max-cuts", type=int, default=5000)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    if a.kaplan:
        gid, cells = kaplan(a.kaplan)
    else:
        gid, cells = a.grid, [tuple(int(v) for v in p.split(",")) for p in a.cells.split()]
    grid = GRIDS[gid]()
    shape = frozenset(grid.normalize(cells))
    contact = grid.contact(CONTACT_MODE)

    t0 = time.time()
    ml = build_ml_formula(shape, grid, contact, a.m)
    print(f"F(S,{a.m}): {ml.num_vars} vars, {len(ml.clauses)} clauses, levels {[len(l) for l in ml.levels]} "
          f"({time.time() - t0:.0f}s)", flush=True)
    total_x = ml.level_offsets[-1] + len(ml.levels[-1])

    def cells_of_var(v):
        lvl, p = ml.placement_of_var(v)
        sym = grid.orientations[p.symmetry_index]
        return frozenset((x + p.tx, y + p.ty) for x, y in map(sym.apply, shape))

    vcells = {v: cells_of_var(v) for v in range(1, total_x + 1)}
    covering = {}
    for v, cs in vcells.items():
        for c in cs:
            covering.setdefault(c, []).append(v)

    cuts = 0
    with Solver(name="cadical153", bootstrap_with=[list(c) for c in ml.clauses]) as s:
        while cuts <= a.max_cuts:
            if not s.solve():
                print(f"UNSAT after {cuts} hole cuts: no hole-free {a.m}-corona exists (Hc < {a.m})")
                return 1
            model = s.get_model()
            chosen = [v for v in range(1, total_x + 1) if model[v - 1] > 0]
            config = decode_model(ml, model)
            placements = config_to_corona_placements(shape, config, grid)
            patch = shape.union(*(vcells[v] for v in chosen))
            holes = holes_of(frozenset(patch), grid)
            if not holes:
                try:
                    cor = check_corona(shape, placements, grid, contact, hole_mode="hc")
                except VerifyError as e:
                    print(f"decoded config rejected by check_corona: {e.code}: {e}")
                    return 2
                print(f"hole-free witness: {cor.max_level} coronas, {len(placements)} placements "
                      f"({cuts} cuts, {time.time() - t0:.0f}s)")
                hdr = gid + " " + " ".join(f"{x} {y}" for x, y in sorted(shape))
                body = [hdr, f"~ {cor.max_level} {cor.max_level} 1", str(len(placements))]
                body += [f"{lvl} {xf.as_text()}" for lvl, xf in zip(cor.levels, (xf for _l, xf in placements))]
                a.out.write_text("\n".join(body) + "\n", encoding="utf-8")
                print(f"wrote {a.out}")
                return 0
            rest, comps = set(holes), []
            while rest:
                st, comp = [rest.pop()], set()
                while st:
                    c = st.pop()
                    comp.add(c)
                    for n in contact.neighbors(c):
                        if n in rest:
                            rest.discard(n)
                            st.append(n)
                comps.append(comp)
            for H in comps:
                ring = {n for c in H for n in contact.neighbors(c)} - H
                cover_h = sorted({v for c in H for v in covering.get(c, ())})
                border = [v for v in chosen if vcells[v] & ring]
                s.add_clause(cover_h + [-v for v in border])
                cuts += 1
            if cuts % 50 < len(comps):
                print(f"  {cuts} hole cuts ({time.time() - t0:.0f}s)", flush=True)
    print("cut budget exhausted")
    return 3


if __name__ == "__main__":
    sys.exit(main())
