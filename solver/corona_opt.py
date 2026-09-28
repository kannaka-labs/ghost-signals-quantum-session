"""corona_opt: the provably best partial next corona for a Heesch witness.

Given a .heesch submission with a complete k-corona witness, find the set of
non-overlapping corona-(k+1) tiles that covers the most of the verifier's
required set R -- exactly (MaxSAT), not heuristically -- then emit a #DEFECT
block and re-check it with the OFFICIAL heesch_verify.defect.verify_defect, so
a result only counts if the real scorer accepts it.

Model (mirrors heesch_verify/defect.py):
  P_k   = hole-free patch of the witness (check_corona, hole_mode "hc")
  R     = required_set(P_k, contact)            # cells touching P_k, not in it
  tile  = orientation o of the shape + translation, disjoint from P_k and from
          every other tile, touching P_k, outside cells enclosed by P_k.
          A tile touches P_k iff it covers some R cell, so anchoring each
          orientation at every R cell enumerates every legal tile exactly.
  score = |R| - |R uncovered| - |pockets enclosed by P_k ∪ tiles| (defect_hc)
Pockets are not in the MaxSAT objective; they are checked afterwards and a
solution with pockets is excluded with a blocking clause and re-solved.

usage: python corona_opt.py path/to/best.heesch [--out improved.heesch] [--timeout 600]
"""
from __future__ import annotations

import argparse
import sys
import time
from fractions import Fraction
from pathlib import Path

from heesch_verify.defect import verify_defect
from heesch_verify.parse import DefectBlock, parse_submission
from heesch_verify.patch import check_corona, required_set
from heesch_verify.shape import holes_of
from heesch_verify.transform import Xform
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF
from pysat.card import CardEnc, EncType

CONTACT_MODE = "point"  # conventions v1: contact "point" (identical to edge on hexes)


def candidate_tiles(shape, grid, P, R, enclosed):
    """Every legal corona-(k+1) placement as (Xform, frozenset cells)."""
    seen, out = set(), []
    for sym in grid.orientations:
        base = [sym.apply(c) for c in shape]
        for r in R:
            for s in base:
                dx, dy = r[0] - s[0], r[1] - s[1]
                if not grid.translation_legal(dx, dy):
                    continue
                cells = frozenset((x + dx, y + dy) for x, y in base)
                if cells in seen:
                    continue
                seen.add(cells)
                if cells & P or cells & enclosed:
                    continue
                xf = Xform(sym.a, sym.b, sym.c0 + dx, sym.d, sym.e, sym.f0 + dy)
                assert xf.apply_all(shape) == cells
                out.append((xf, cells))
    return out


def solve(tiles, R, timeout):
    """MaxSAT: at most one tile per cell (hard), cover each R cell (soft, weight 1)."""
    w = WCNF()
    var = {i: i + 1 for i in range(len(tiles))}
    top = len(tiles)
    by_cell = {}
    for i, (_xf, cells) in enumerate(tiles):
        for c in cells:
            by_cell.setdefault(c, []).append(var[i])
    for c, vs in by_cell.items():
        if len(vs) > 1:
            enc = CardEnc.atmost(lits=vs, bound=1, top_id=top, encoding=EncType.seqcounter)
            top = max(top, enc.nv)
            for cl in enc.clauses:
                w.append(cl)
    for r in R:
        vs = by_cell.get(r, [])
        # soft: r covered; an R cell no tile can reach is simply unsatisfiable-soft
        w.append(vs if vs else [top + 1], weight=1)
        if not vs:
            top += 1
            w.append([-top])  # force the dummy false: r is uncoverable
    return w, var


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--max-rounds", type=int, default=50, help="pocket-exclusion re-solves")
    a = ap.parse_args()

    text = a.submission.read_text(encoding="utf-8")
    sub = parse_submission(text)
    grid, shape = sub.grid, frozenset(sub.cells)
    contact = grid.contact(CONTACT_MODE)
    corona = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
    P = corona.patch_cells
    R = required_set(P, contact)
    enclosed = holes_of(P, grid)
    k = corona.max_level
    print(f"grid={sub.grid_id} cells={len(shape)} coronas={k} |P|={len(P)} |R|={len(R)} enclosed={len(enclosed)}")
    if sub.defect is not None:
        print(f"submitted defect: level {sub.defect.level} u_hc={sub.defect.u_hc} u_hh={sub.defect.u_hh} "
              f"required={sub.defect.required} tiles={len(sub.defect.tiles)}")

    tiles = candidate_tiles(shape, grid, P, R, enclosed)
    print(f"candidate corona-{k + 1} tiles: {len(tiles)}")

    w, var = solve(tiles, R, None)
    best = None
    for rnd in range(a.max_rounds):
        t0 = time.time()
        with RC2(w) as rc2:
            model = rc2.compute()
            cost = rc2.cost
        chosen = [i for i in range(len(tiles)) if model[var[i] - 1] > 0]
        covered = frozenset().union(*(tiles[i][1] for i in chosen)) if chosen else frozenset()
        uncovered = R - covered
        pockets = holes_of(frozenset(P | covered), grid)
        print(f"round {rnd}: MaxSAT cost={cost} uncovered={len(uncovered)} pockets={len(pockets)} "
              f"tiles={len(chosen)} ({time.time() - t0:.1f}s)")
        if not pockets:
            best = (chosen, uncovered)
            break
        w.append([-var[i] for i in chosen])  # exclude this exact tile set and re-solve
    if best is None:
        print("no pocket-free optimum found within max-rounds")
        return 2

    chosen, uncovered = best
    d = len(uncovered)
    frac = Fraction(len(R) - d, len(R))
    print(f"\nOPTIMUM (pocket-free): uncovered {d} of {len(R)} -> fraction {float(frac):.6f} -> score {k + float(frac):.6f}")
    if sub.defect is not None and sub.defect.required == len(R):
        print(f"vs submitted: {sub.defect.u_hc} uncovered -> score {k + (len(R) - sub.defect.u_hc) / len(R):.6f}")

    block = DefectBlock(level=k + 1, u_hc=d, u_hh=d, required=len(R),
                        tiles=tuple((k + 1, tiles[i][0]) for i in chosen))
    res = verify_defect(shape, grid, corona, block, contact)
    print(f"OFFICIAL verify_defect: defect_hc={res.defect_hc} defect_hh={res.defect_hh} required={res.required} "
          f"pockets={res.pocket_cells} tiles={res.partial_tiles}")

    if a.out:
        lines = text.splitlines()
        cut = next((i for i, l in enumerate(lines) if l.startswith("#DEFECT") or l.startswith("#PROOF")), len(lines))
        tail = lines[cut:]
        proof_at = next((i for i, l in enumerate(tail) if l.startswith("#PROOF")), None)
        proof_tail = tail[proof_at:] if proof_at is not None else []
        body = lines[:cut] + [f"#DEFECT {k + 1} {res.defect_hc} {res.defect_hh} {res.required}", str(len(chosen))]
        body += [f"{k + 1} {tiles[i][0].as_text()}" for i in chosen]
        a.out.write_text("\n".join(body + proof_tail) + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
