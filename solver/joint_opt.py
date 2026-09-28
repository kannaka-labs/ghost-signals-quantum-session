"""joint_opt: choose corona k AND the partial corona k+1 together, minimising ring-(k+1) defect.

Keeps coronas 0..k-1 of a witness fixed (patch P_{k-1}) and solves ONE MaxSAT:
  x_t  ring-k tile t (universe around P_{k-1}, from the verifier's own encoder)
  y_u  ring-(k+1) tile u (legal placements disjoint from P_{k-1}, not touching it)
Hard:
  - every cell holds at most one chosen tile (x and y together);
  - ring k is complete: every cell of R(P_{k-1}) is covered by some x;
  - y_u -> OR(x_t touching u)             (u touches P_k, so it is in corona k+1)
Soft (weight 1 per cell c in the ring-(k+1) band):
  c is "required and uncovered" if it touches a chosen x, is not covered by any
  x, and is not covered by any y. Encoded with r_c:
     (-x_t v OR x_covering_c v r_c)  for each x_t touching c     (r_c forced when required)
     soft: (-r_c v OR y_covering_c)                              (pay 1 if not covered)
Holes in P_k are excluded lazily with the sound cut used by corona_sampler.
Pockets of the ring-(k+1) partial are not in the objective; the final solution
is re-checked with the OFFICIAL check_corona + verify_defect, which count them.

The submitted witness is a feasible point, so the optimum is <= its defect.

usage: python joint_opt.py best.heesch [--out improved.heesch] [--max-cuts 400]
"""
from __future__ import annotations

import argparse
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corona_opt import CONTACT_MODE  # noqa: E402
from corona_sampler import to_xform  # noqa: E402

from heesch_encoder.clauses import build_formula  # noqa: E402
from heesch_verify.defect import verify_defect  # noqa: E402
from heesch_verify.parse import DefectBlock, parse_submission  # noqa: E402
from heesch_verify.patch import check_corona, required_set  # noqa: E402
from heesch_verify.shape import holes_of  # noqa: E402
from heesch_verify.transform import Xform  # noqa: E402
from pysat.card import CardEnc, EncType  # noqa: E402
from pysat.examples.rc2 import RC2  # noqa: E402
from pysat.formula import WCNF  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--max-cuts", type=int, default=400)
    ap.add_argument("--decide", default=None, metavar="U/RMIN",
                    help="SAT decision instead of optimisation: is there a hole- and pocket-free choice with "
                         "uncovered <= U and |R| >= RMIN? UNSAT (with sound cuts) proves it impossible.")
    ap.add_argument("--maximize-ring", action="store_true",
                    help="lexicographic objective: fewest uncovered, then the LARGEST required set "
                         "(the score is a ratio, so equal defect over a bigger ring scores higher)")
    a = ap.parse_args()

    text = a.submission.read_text(encoding="utf-8")
    sub = parse_submission(text)
    grid, shape = sub.grid, frozenset(sub.cells)
    contact = grid.contact(CONTACT_MODE)
    base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
    k = base.max_level
    inner = [pl for pl, lvl in zip(sub.patches[0], base.levels) if lvl < k]
    Pp = frozenset().union(*(base.level_cells[i] for i in range(k)))  # P_{k-1}
    nbr = lambda cells: {n for c in cells for n in contact.neighbors(c)}  # noqa: E731

    # ring-k universe from the verifier's own encoder
    f = build_formula(shape, Pp, grid, contact)
    X = list(f.universe)
    xcells = [frozenset((x + p.tx, y + p.ty) for x, y in map(grid.orientations[p.symmetry_index].apply, shape)) for p in X]
    band_k = frozenset().union(*xcells)                       # cells ring k can occupy
    Rp = required_set(Pp, contact)

    # ring-(k+1) candidates: disjoint from P_{k-1}, NOT touching it, touching some ring-k cell
    near = (nbr(band_k) | band_k) - Pp
    Pp_touch = nbr(Pp) | Pp
    seen, Y, ycells = set(), [], []
    for si, sym in enumerate(grid.orientations):
        img = [sym.apply(c) for c in shape]
        for h in near:
            for s in img:
                dx, dy = h[0] - s[0], h[1] - s[1]
                if not grid.translation_legal(dx, dy):
                    continue
                cells = frozenset((x + dx, y + dy) for x, y in img)
                if cells in seen:
                    continue
                seen.add(cells)
                if cells & Pp_touch:        # overlaps P_{k-1} or touches it -> not corona k+1
                    continue
                if not (nbr(cells) & band_k):
                    continue
                Y.append(Xform(sym.a, sym.b, sym.c0 + dx, sym.d, sym.e, sym.f0 + dy))
                ycells.append(cells)
    nx, ny = len(X), len(Y)
    xv = lambda i: i + 1            # noqa: E731
    yv = lambda j: nx + j + 1       # noqa: E731
    top = nx + ny
    print(f"k={k}: ring-{k} universe {nx}, ring-{k + 1} candidates {ny}")

    w = WCNF()
    occ = {}
    for i, cs in enumerate(xcells):
        for c in cs:
            occ.setdefault(c, []).append(xv(i))
    for j, cs in enumerate(ycells):
        for c in cs:
            occ.setdefault(c, []).append(yv(j))
    for c, vs in occ.items():
        if len(vs) > 1:
            enc = CardEnc.atmost(lits=vs, bound=1, top_id=top, encoding=EncType.seqcounter)
            top = max(top, enc.nv)
            for cl in enc.clauses:
                w.append(cl)
    xcov = {}
    for i, cs in enumerate(xcells):
        for c in cs:
            xcov.setdefault(c, []).append(xv(i))
    for c in Rp:                                             # ring k complete
        w.append(xcov.get(c, []))
    xtouch = {}                                              # cell -> ring-k tiles touching it
    for i, cs in enumerate(xcells):
        for c in nbr(cs) - cs:
            xtouch.setdefault(c, []).append(xv(i))
    for j, cs in enumerate(ycells):                          # y touches a chosen x
        w.append([-yv(j)] + sorted({v for c in cs for v in xtouch.get(c, ())}))
    ycov = {}
    for j, cs in enumerate(ycells):
        for c in cs:
            ycov.setdefault(c, []).append(yv(j))
    band = [c for c in xtouch if c not in Pp]
    rvar, uvar = {}, {}
    exact = a.maximize_ring or a.decide
    W = (len(band) + 1) if a.maximize_ring else 1    # lexicographic: uncovered first, then |R|
    for c in band:
        top += 1
        rvar[c] = top
        for t in xtouch[c]:
            w.append([-t] + xcov.get(c, []) + [top])       # required  ->  r_c
        if exact:
            # r_c exactly "required": r_c -> touches a chosen x, and r_c -> c not in ring k
            w.append([-top] + xtouch[c])
            for t in xcov.get(c, []):
                w.append([-top, -t])
        if a.decide:
            top += 1
            uvar[c] = top                                    # u_c >= r_c and not covered by ring k+1
            w.append([-rvar[c]] + ycov.get(c, []) + [top])
        else:
            if a.maximize_ring:
                w.append([top], weight=1)                    # reward a larger required set
            w.append([-top] + ycov.get(c, []), weight=W)
    if a.decide:
        u_max, r_min = (int(v) for v in a.decide.split("/"))
        for enc in (CardEnc.atmost(lits=list(uvar.values()), bound=u_max, top_id=top, encoding=EncType.totalizer),):
            top = max(top, enc.nv)
            for cl in enc.clauses:
                w.append(cl)
        enc = CardEnc.atleast(lits=list(rvar.values()), bound=r_min, top_id=top, encoding=EncType.totalizer)
        top = max(top, enc.nv)
        for cl in enc.clauses:
            w.append(cl)
        print(f"DECIDE: uncovered <= {u_max} and |R| >= {r_min}  (beats {u_max}/{r_min - 1} iff SAT)")
    print(f"band cells {len(band)}, clauses {len(w.hard)} hard / {len(w.soft)} soft")

    # submitted witness as a reference point (its x set and y set)
    t0, cuts, result = time.time(), 0, None
    sat = None
    if a.decide:
        from pysat.solvers import Solver
        sat = Solver(name="cadical153", bootstrap_with=w.hard)
    while cuts <= a.max_cuts:
        if a.decide:
            if not sat.solve():
                print(f"\nUNSAT after {cuts} sound cuts ({time.time() - t0:.0f}s): NO hole-free, pocket-free "
                      f"ring {k}/{k + 1} choice over these fixed inner rings has uncovered <= {u_max} with "
                      f"|R| >= {r_min}. The submitted ratio cannot be beaten this way.")
                return 1
            m = sat.get_model()
            cost = 0
        else:
            with RC2(w) as rc2:
                m = rc2.compute()
                cost = rc2.cost
        pos = {l for l in m if l > 0}
        cx = [i for i in range(nx) if xv(i) in pos]
        cy = [j for j in range(ny) if yv(j) in pos]
        Pk = Pp.union(*(xcells[i] for i in cx))
        holes = holes_of(frozenset(Pk), grid)
        # Pockets: empty cells enclosed by P_k plus the chosen ring-(k+1) tiles. The
        # official scorer counts them in defect_hc, so they are cut away too.
        pockets = frozenset() if holes else holes_of(frozenset(Pk.union(*(ycells[j] for j in cy))), grid)
        # The scorer counts |uncovered R  UNION  pockets|: an enclosed cell that is itself an
        # uncovered REQUIRED cell costs nothing extra (the leader has two such cells). Only
        # pocket cells outside R(P_k) add cost, so only components containing one are cut.
        # (Cutting every pocket, as an earlier version did, excluded valid solutions.)
        if pockets:
            R_now = required_set(frozenset(Pk), contact)
            extra = pockets - R_now
            if not extra:
                pockets = frozenset()
            else:
                keep, rest0 = set(), set(pockets)
                while rest0:
                    st, comp = [rest0.pop()], set()
                    while st:
                        c = st.pop()
                        comp.add(c)
                        for n in contact.neighbors(c):
                            if n in rest0:
                                rest0.discard(n)
                                st.append(n)
                    if comp & extra:
                        keep |= comp
                pockets = frozenset(keep)
        nreq = sum(1 for c in band if rvar[c] in pos)
        unc = (cost // W) if a.maximize_ring else cost
        print(f"solve: uncovered~{unc} |R|~{nreq} ring{k}={len(cx)} ring{k + 1}={len(cy)} holes={len(holes)} "
              f"pockets={len(pockets)} ({time.time() - t0:.0f}s, {cuts} cuts)", flush=True)
        if not holes and not pockets:
            result = (cost, cx, cy, Pk)
            break
        bad = holes or pockets
        comps, rest = [], set(bad)
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
            ring_h = nbr(H) - H
            if holes:   # a hole in P_k: only ring-k tiles can cover or open it
                cover_h = sorted({v for c in H for v in xcov.get(c, ())})
                border = [xv(i) for i in cx if xcells[i] & ring_h]
            else:       # a pocket: either ring may cover it, either ring's border may open it
                cover_h = sorted({v for c in H for v in [*xcov.get(c, ()), *ycov.get(c, ())]})
                border = [xv(i) for i in cx if xcells[i] & ring_h] + [yv(j) for j in cy if ycells[j] & ring_h]
            w.append(cover_h + [-v for v in border])
            if sat is not None:
                sat.add_clause(cover_h + [-v for v in border])
            cuts += 1
    if result is None:
        print("no hole-free optimum within the cut budget")
        return 2

    cost, cx, cy, Pk = result
    ring = [(k, to_xform(grid, X[i])) for i in cx]
    corona = check_corona(shape, list(inner) + ring, grid, contact, hole_mode="hc")
    assert corona.max_level == k, corona.max_level
    R = required_set(corona.patch_cells, contact)
    block = DefectBlock(level=k + 1, u_hc=10**6, u_hh=10**6, required=len(R), tiles=tuple((k + 1, Y[j]) for j in cy))
    res = verify_defect(shape, grid, corona, block, contact)
    frac = Fraction(len(R) - res.defect_hc, len(R))
    print(f"\nOFFICIAL: ring-{k} valid (hole-free), ring-{k + 1} defect_hc={res.defect_hc} (hh={res.defect_hh}, "
          f"pockets={res.pocket_cells}) of {res.required} -> score {k + float(frac):.6f}")
    if sub.defect:
        print(f"submitted: {sub.defect.u_hc}/{sub.defect.required} -> {k + (sub.defect.required - sub.defect.u_hc) / sub.defect.required:.6f}")
    if a.out:
        hdr = text.splitlines()[0]
        body = [hdr, f"~ {k} {k} 1", str(len(inner) + len(ring))]
        body += [f"{lvl} {xf.as_text()}" for lvl, xf in list(inner) + ring]
        body += [f"#DEFECT {k + 1} {res.defect_hc} {res.defect_hh} {res.required}", str(len(cy))]
        body += [f"{k + 1} {Y[j].as_text()}" for j in cy]
        a.out.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"wrote {a.out} (no #PROOF: regenerate with tools/prove.py; the shape is unchanged so the old proof applies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
