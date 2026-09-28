"""corona_sampler: vary the corona-k patch, keep the one whose ring k+1 is most coverable.

For a submission with a k-corona witness, keep coronas 0..k-1, draw many
distinct complete corona-k rings from the verifier's OWN single-level encoder
(heesch_encoder.clauses.build_formula: models = complete coronas around P_{k-1}),
keep those whose full patch passes the verifier's check_corona(hole_mode="hc"),
and for each resulting P_k compute the EXACT minimum number of ring-(k+1)
required cells left uncovered (MaxSAT lower bound, corona_opt.solve).

A P_k beats a submitted defect d/|R| when lb/|R'| < d/|R|. Pockets can only
add to the defect, so lb is a true lower bound; realise promising ones with
corona_opt.py afterwards.

usage: python corona_sampler.py best.heesch [--samples 200] [--save-best out.heesch]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corona_opt import candidate_tiles, solve, CONTACT_MODE  # noqa: E402

from heesch_encoder.clauses import build_formula  # noqa: E402
from heesch_verify.parse import parse_submission  # noqa: E402
from heesch_verify.patch import check_corona, required_set  # noqa: E402
from heesch_verify.result import VerifyError  # noqa: E402
from heesch_verify.shape import holes_of  # noqa: E402
from heesch_verify.transform import Xform  # noqa: E402
from pysat.examples.rc2 import RC2  # noqa: E402
from pysat.solvers import Solver  # noqa: E402


def to_xform(grid, p):
    s = grid.orientations[p.symmetry_index]
    return Xform(s.a, s.b, s.c0 + p.tx, s.d, s.e, s.f0 + p.ty)


def ring_lower_bound(shape, grid, contact, P):
    R = required_set(P, contact)
    tiles = candidate_tiles(shape, grid, P, R, holes_of(P, grid))
    w, _var = solve(tiles, R, None)
    with RC2(w) as rc2:
        rc2.compute()
        return rc2.cost, len(R)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", type=Path)
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--save-best", type=Path, default=None)
    a = ap.parse_args()

    text = a.submission.read_text(encoding="utf-8")
    sub = parse_submission(text)
    grid, shape = sub.grid, frozenset(sub.cells)
    contact = grid.contact(CONTACT_MODE)
    base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
    k = base.max_level
    inner = [pl for pl, lvl in zip(sub.patches[0], base.levels) if lvl < k]
    P_prev = frozenset().union(*(base.level_cells[i] for i in range(k)))
    ref_lb, ref_R = ring_lower_bound(shape, grid, contact, base.patch_cells)
    ref = (sub.defect.u_hc / sub.defect.required) if sub.defect else ref_lb / ref_R
    print(f"shape {len(shape)} cells, k={k}; reference ring-{k + 1}: lb={ref_lb}/{ref_R}, "
          f"submitted {sub.defect.u_hc if sub.defect else '-'}/{sub.defect.required if sub.defect else '-'} "
          f"(ratio {ref:.5f}, score {k + 1 - ref:.5f})")

    f = build_formula(shape, P_prev, grid, contact)
    nU = len(f.universe)
    print(f"corona-{k} universe around P_{k - 1}: {nU} placements, {len(f.clauses)} clauses")

    # Lazy hole cuts. For an enclosed empty component H, every hole-free ring must
    # either cover a cell of H or drop a chosen tile bordering H (if both stay as
    # they are, H's boundary is intact and H stays enclosed), so the clause
    # (OR tiles covering H) v (OR -bordering chosen tiles) is sound.
    cells_of = [frozenset((x + p.tx, y + p.ty) for x, y in map(grid.orientations[p.symmetry_index].apply, shape))
                for p in f.universe]
    covering = {}
    for v, cells in enumerate(cells_of, start=1):
        for c in cells:
            covering.setdefault(c, []).append(v)

    def components(cells):
        cells, out = set(cells), []
        while cells:
            stack, comp = [cells.pop()], set()
            while stack:
                c = stack.pop()
                comp.add(c)
                for n in contact.neighbors(c):
                    if n in cells:
                        cells.discard(n)
                        stack.append(n)
            out.append(comp)
        return out

    best = None
    seen_valid = cuts = 0
    t0 = time.time()
    with Solver(name="cadical153", bootstrap_with=[list(c) for c in f.clauses]) as s:
        i = 0
        while i < a.samples:
            if not s.solve():
                print(f"exhausted after {i} rings ({cuts} hole cuts)")
                break
            model = s.get_model()
            chosen = [v for v in range(1, nU + 1) if model[v - 1] > 0]
            patch = P_prev.union(*(cells_of[v - 1] for v in chosen))
            holes = holes_of(frozenset(patch), grid)
            if holes:
                for H in components(holes):
                    cover_h = sorted({v for c in H for v in covering.get(c, ())})
                    nbrs = {n for c in H for n in contact.neighbors(c)} - H
                    border = [v for v in chosen if cells_of[v - 1] & nbrs]
                    s.add_clause(cover_h + [-v for v in border])
                    cuts += 1
                continue  # re-solve; not a sample
            i += 1
            s.add_clause([-v for v in chosen])  # a different ring next time
            ring = [(k, to_xform(grid, f.universe[v - 1])) for v in chosen]
            try:
                cor = check_corona(shape, list(inner) + ring, grid, contact, hole_mode="hc")
            except VerifyError:
                continue  # holes, or a tile that recomputes to another level
            if cor.max_level != k:
                continue
            seen_valid += 1
            lb, nR = ring_lower_bound(shape, grid, contact, cor.patch_cells)
            ratio = lb / nR
            tag = ""
            if best is None or ratio < best[0]:
                best = (ratio, lb, nR, list(inner) + ring)
                tag = "  <-- best so far" + ("  *** BEATS SUBMITTED ***" if ratio < ref else "")
            print(f"ring {i:4d}: valid P_{k}, ring-{k + 1} lb {lb}/{nR} = {ratio:.5f} "
                  f"(score <= {k + 1 - ratio:.5f}){tag}", flush=True)
    print(f"\n{seen_valid} valid hole-free P_{k} of {i} drawn ({cuts} hole cuts) in {time.time() - t0:.0f}s")
    if best:
        ratio, lb, nR, placements = best
        print(f"BEST: lb {lb}/{nR} = {ratio:.5f} -> score ceiling {k + 1 - ratio:.5f} "
              f"vs submitted {k + 1 - ref:.5f}")
        if a.save_best:
            lines = text.splitlines()
            hdr = lines[0]
            body = [hdr, f"~ {k} {k} 1", str(len(placements))] + [f"{lvl} {xf.as_text()}" for lvl, xf in placements]
            a.save_best.write_text("\n".join(body) + "\n", encoding="utf-8")
            print(f"wrote witness-only {a.save_best} (no #DEFECT/#PROOF; realise with corona_opt.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
