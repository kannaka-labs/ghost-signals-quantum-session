"""joint_multi: re-choose rings f..k AND the partial ring k+1 together (SAT decision).

Keeps coronas 0..f-1 of a witness fixed (patch P_{f-1}); every ring f..k is free.
Variables z[l][p] = placement p used at level l (l = f..k+1; level k+1 is the partial ring).
Hard constraints:
  - occupancy: every cell holds at most one tile across ALL levels;
  - ring f complete: every cell of R(P_{f-1}) covered by a level-f tile;
  - ring l complete (f < l <= k): a cell touching a chosen level-(l-1) tile, not covered at
    any level < l (and not in P_{f-1}), must be covered by a level-l tile;
  - every level-l tile (l > f) touches a chosen level-(l-1) tile;
    (level correctness then follows: ring l-1 is complete around P_{l-2}, so every cell
    touching P_{l-2} is occupied by ring l-1, and a level-l tile cannot touch P_{l-2});
  - partial ring k+1: r_c exact "required" (touches a chosen level-k tile, not covered at
    any level <= k), u_c >= r_c and not covered at level k+1;
    DECIDE: sum(u) <= U and sum(r) >= RMIN.
Lazy sound cuts: a hole in P_l -> (OR tiles of levels <= l covering it) v (OR -chosen bordering
level <= l tiles); an extra pocket (a pocket component with a NON-required cell) likewise
over all levels. Final answer re-checked with the OFFICIAL check_corona + verify_defect.
CONTROL: the submitted witness is feasible, so `--decide <its defect>/<its |R|>` must be SAT.

usage: python joint_multi.py best.heesch --free-from 3 --decide 3/255 [--out f.heesch]
"""
from __future__ import annotations

import argparse
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corona_opt import CONTACT_MODE  # noqa: E402

from heesch_encoder.clauses import build_formula  # noqa: E402
from heesch_verify.defect import verify_defect  # noqa: E402
from heesch_verify.parse import DefectBlock, parse_submission  # noqa: E402
from heesch_verify.patch import check_corona, required_set  # noqa: E402
from heesch_verify.shape import holes_of  # noqa: E402
from heesch_verify.transform import Xform  # noqa: E402
from pysat.card import CardEnc, EncType, ITotalizer  # noqa: E402
from pysat.solvers import Solver  # noqa: E402


def peak_gb():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20   # KiB on Linux
    except ImportError:                                                     # Windows: no resource module
        return float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission", type=Path)
    ap.add_argument("--free-from", type=int, required=True, help="first free ring f (rings f..k are re-chosen)")
    ap.add_argument("--decide", required=True, metavar="U/RMIN")
    ap.add_argument("--max-cuts", type=int, default=20000)
    ap.add_argument("--r-only", action="store_true",
                    help="decide only |R| >= RMIN: no defect bound, extra pockets allowed (complete rings stay hole-free)")
    ap.add_argument("--count-pockets", action="store_true",
                    help="U bounds the OFFICIAL defect |uncovered R + pocket cells| instead of forbidding extra pockets")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--export-cnf", type=Path, default=None,
                    help="write the solver's FINAL static clause set (base + every lazy cut + totalizer extensions + "
                         "final assumptions as unit clauses) as DIMACS, plus <path>.map.json (and <path>.model if SAT)")
    ap.add_argument("--oracle", type=Path, default=None,
                    help="with --export-cnf: solve every iteration with this stock solver binary (cadical/kissat, "
                         "exit 10/20, `v` lines) from scratch instead of incremental pysat")
    a = ap.parse_args()
    assert not a.oracle or a.export_cnf, "--oracle needs --export-cnf"
    U, RMIN = (int(v) for v in a.decide.split("/"))

    text = a.submission.read_text(encoding="utf-8")
    sub = parse_submission(text)
    grid, shape = sub.grid, frozenset(sub.cells)
    contact = grid.contact(CONTACT_MODE)
    base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
    k, f = base.max_level, a.free_from
    assert 1 <= f <= k
    fixed = [pl for pl, lvl in zip(sub.patches[0], base.levels) if lvl < f]
    P0 = frozenset().union(*(base.level_cells[i] for i in range(f)))       # P_{f-1}
    nbr = lambda cells: {n for c in cells for n in contact.neighbors(c)}    # noqa: E731
    P0_touch = nbr(P0) | P0

    def img_cells(sym, dx, dy, img):
        return frozenset((x + dx, y + dy) for x, y in img)

    # candidate tiles per level
    levels = list(range(f, k + 2))                  # f..k complete, k+1 partial
    cand = {}                                       # level -> list of (Xform, cells)
    uni = build_formula(shape, P0, grid, contact).universe
    cand[f] = []
    for p in uni:
        s = grid.orientations[p.symmetry_index]
        cand[f].append((Xform(s.a, s.b, s.c0 + p.tx, s.d, s.e, s.f0 + p.ty),
                        img_cells(s, p.tx, p.ty, [s.apply(c) for c in shape])))
    for l in levels[1:]:
        prev_cells = set().union(*(cs for _xf, cs in cand[l - 1]))
        anchor = nbr(prev_cells) - P0
        # seen is keyed by (orientation, dx, dy), not by the cell set: holding every rejected image's frozenset is what
        # OOM-killed the 25 GB pod at f=1. A symmetric shape can repeat a cell set under two keys; the duplicate is a
        # harmless extra variable (occupancy makes the pair exclusive).
        seen, out = set(), []
        for si, s in enumerate(grid.orientations):
            img = [s.apply(c) for c in shape]
            for h in anchor:
                for c0 in img:
                    dx, dy = h[0] - c0[0], h[1] - c0[1]
                    if (si, dx, dy) in seen or not grid.translation_legal(dx, dy):
                        continue
                    seen.add((si, dx, dy))
                    cs = img_cells(s, dx, dy, img)
                    if cs & P0_touch:
                        continue
                    if not (nbr(cs) & prev_cells):
                        continue
                    out.append((Xform(s.a, s.b, s.c0 + dx, s.d, s.e, s.f0 + dy), cs))
        cand[l] = out
    print("candidates per level:", {l: len(cand[l]) for l in levels}, f"peak RSS {peak_gb():.1f} GB", flush=True)

    var, top = {}, 0
    for l in levels:
        for i in range(len(cand[l])):
            top += 1
            var[(l, i)] = top
    s = Solver(name="cadical153")                   # clauses stream straight in: no second copy in Python
    nclauses = 0
    # DRAT export hook: tee EVERY clause the solver receives (including hole/pocket cuts, which bypass add()) to a
    # body file, so the export is the solver's own clause set, not a re-implementation.
    exp = None
    if a.export_cnf:
        exp = {"body": open(str(a.export_cnf) + ".body", "w", buffering=1 << 22), "n": 0, "maxv": 0}
        _orig_add_clause = s.add_clause

        def _tee_add_clause(cl, no_return=True):
            cl = [int(x) for x in cl]
            exp["body"].write(" ".join(map(str, cl)) + " 0\n")
            exp["n"] += 1
            if cl:
                exp["maxv"] = max(exp["maxv"], max(abs(x) for x in cl))
            return _orig_add_clause(cl, no_return)
        s.add_clause = _tee_add_clause

    def export(assumptions, status, model=None):
        """Close the body and write DIMACS = header + body + one unit clause per final assumption."""
        import hashlib
        import json
        import os
        body = str(a.export_cnf) + ".body"
        exp["body"].close()
        units = [int(x) for x in assumptions]
        nv = max([exp["maxv"], top] + [abs(x) for x in units])
        with open(a.export_cnf, "wb") as out:
            out.write(f"c joint_multi export: {a.submission.name} --free-from {f} --decide {U}/{RMIN}"
                      f"{' --count-pockets' if a.count_pockets else ''}{' --r-only' if a.r_only else ''}"
                      f" status={status} solver_clauses={exp['n']} assumption_units={len(units)}\n".encode())
            out.write(f"p cnf {nv} {exp['n'] + len(units)}\n".encode())
            with open(body, "rb") as b:
                while True:
                    chunk = b.read(1 << 24)
                    if not chunk:
                        break
                    out.write(chunk)
            for x in units:
                out.write(f"{x} 0\n".encode())
        os.remove(body)
        zmap = {str(var[(l, i)]): [l, cand[l][i][0].as_text()] for (l, i) in var}
        meta = {"submission": str(a.submission.resolve()), "free_from": f, "k": k, "U": U, "RMIN": RMIN,
                "count_pockets": a.count_pockets, "r_only": a.r_only, "status": status, "nvars": nv,
                "solver_clauses": exp["n"], "assumptions": units, "cuts": cuts, "z": zmap}
        Path(str(a.export_cnf) + ".map.json").write_text(json.dumps(meta), encoding="utf-8")
        if model is not None:
            Path(str(a.export_cnf) + ".model").write_text(" ".join(map(str, model)) + " 0\n", encoding="utf-8")
        h = hashlib.sha256()
        with open(a.export_cnf, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        print(f"EXPORT {a.export_cnf}: p cnf {nv} {exp['n'] + len(units)} ({exp['n']} solver clauses + "
              f"{len(units)} assumption units) sha256 {h.hexdigest()}", flush=True)

    def add(cl):
        nonlocal nclauses
        s.add_clause(cl)
        nclauses += 1

    def add_all(cls):
        for cl in cls:
            add(cl)

    cover = {}                                      # cell -> [(level, var)]
    for (l, i), v in var.items():
        for c in cand[l][i][1]:
            cover.setdefault(c, []).append((l, v))
    for c, lv in cover.items():                     # occupancy across all levels
        vs = [v for _l, v in lv]
        if len(vs) > 1:
            enc = CardEnc.atmost(lits=vs, bound=1, top_id=top, encoding=EncType.seqcounter)
            top = max(top, enc.nv)
            add_all(enc.clauses)
    cov_at = lambda c, pred: [v for l, v in cover.get(c, ()) if pred(l)]  # noqa: E731
    for c in required_set(P0, contact):             # ring f complete
        add(cov_at(c, lambda l: l == f))
    touch = {}                                      # (level, cell) -> vars of that level touching the cell
    for (l, i), v in var.items():
        cs = cand[l][i][1]
        for c in nbr(cs) - cs:
            touch.setdefault((l, c), []).append(v)
    for l in levels[1:]:                            # each tile touches a chosen tile one level down
        for i in range(len(cand[l])):
            cs = cand[l][i][1]
            add([-var[(l, i)]] + sorted({v for c in cs for v in touch.get((l - 1, c), ())}))
    for l in range(f + 1, k + 1):                   # rings f+1..k complete
        for (lt, c), ts in touch.items():
            if lt != l - 1 or c in P0:
                continue
            lower = cov_at(c, lambda x: x < l)
            here = cov_at(c, lambda x: x == l)
            for t in ts:
                add([-t] + lower + here)
    rvar, uvar = {}, {}                             # partial ring k+1
    for (lt, c), ts in touch.items():
        if lt != k or c in P0:
            continue
        top += 1
        r = top
        rvar[c] = r
        low = cov_at(c, lambda x: x <= k)
        for t in ts:
            add([-t] + low + [r])
        add([-r] + ts)
        for v in low:
            add([-r, -v])
        top += 1
        uvar[c] = top
        add([-r] + cov_at(c, lambda x: x == k + 1) + [top])
    assume, tot, ecell, pockets_seen = [], None, {}, set()
    if a.r_only:
        pass                                        # no defect constraint at all
    elif a.count_pockets:                           # defect counter that grows as pockets are discovered
        tot = ITotalizer(lits=list(uvar.values()), ubound=U, top_id=top)
        top = max(top, tot.top_id)
        add_all(tot.cnf.clauses)
        assume = [-tot.rhs[U]]                      # rhs[j] <=> count >= j+1
    else:
        enc = CardEnc.atmost(lits=list(uvar.values()), bound=U, top_id=top, encoding=EncType.totalizer)
        top = max(top, enc.nv)
        add_all(enc.clauses)
    enc = CardEnc.atleast(lits=list(rvar.values()), bound=RMIN, top_id=top, encoding=EncType.totalizer)
    top = max(top, enc.nv)
    add_all(enc.clauses)
    print(f"vars {top}, clauses {nclauses}, peak RSS {peak_gb():.1f} GB; DECIDE uncovered <= {U}, |R| >= {RMIN}", flush=True)

    def comps(cells):
        rest, out = set(cells), []
        while rest:
            st, comp = [rest.pop()], set()
            while st:
                c = st.pop()
                comp.add(c)
                for n in contact.neighbors(c):
                    if n in rest:
                        rest.discard(n)
                        st.append(n)
            out.append(comp)
        return out

    def oracle_solve(assumptions):
        """--oracle: answer this iteration with a STOCK solver binary run from scratch on the current static CNF
        (every clause so far + assumptions as units) instead of pysat. The lazy-cut code is unchanged."""
        import subprocess
        import tempfile
        exp["body"].flush()
        units = [int(x) for x in assumptions]
        nv = max([exp["maxv"], top] + [abs(x) for x in units])
        with tempfile.TemporaryFile() as outf:
            ts = time.time()
            p = subprocess.Popen([str(a.oracle), "-q"], stdin=subprocess.PIPE, stdout=outf)
            p.stdin.write(f"p cnf {nv} {exp['n'] + len(units)}\n".encode())
            with open(str(a.export_cnf) + ".body", "rb") as b:
                while True:
                    chunk = b.read(1 << 24)
                    if not chunk:
                        break
                    p.stdin.write(chunk)
            for x in units:
                p.stdin.write(f"{x} 0\n".encode())
            p.stdin.close()
            rc = p.wait()
            outf.seek(0)
            lines = outf.read().decode().splitlines()
        print(f"  oracle {a.oracle.name}: rc={rc} on {exp['n'] + len(units)} clauses ({time.time() - ts:.0f}s)",
              flush=True)
        if rc == 20:
            return None
        if rc != 10:
            raise SystemExit(f"oracle failed rc={rc}")
        return [int(x) for ln in lines if ln.startswith("v") for x in ln.split()[1:] if x != "0"]

    t0, cuts = time.time(), 0
    with s:
        while cuts <= a.max_cuts:
            if a.oracle:
                model_now = oracle_solve(assume)
            else:
                model_now = s.get_model() if s.solve(assumptions=assume) else None
            if model_now is None:
                what = (f"OFFICIAL defect (uncovered + pocket cells) <= {U}" if a.count_pockets
                        else f"uncovered <= {U} without extra pockets")
                print(f"\nUNSAT after {cuts} sound cuts ({time.time() - t0:.0f}s): with rings 0..{f - 1} fixed, no "
                      f"choice of rings {f}..{k + 1} has {what} over |R| >= {RMIN}.")
                if exp:
                    export(assume, "UNSAT")
                return 1
            pos = {x for x in model_now if x > 0}
            chosen = {l: [i for i in range(len(cand[l])) if var[(l, i)] in pos] for l in levels}
            added, P = 0, set(P0)
            for l in range(f, k + 1):               # holes level by level
                P |= set().union(*(cand[l][i][1] for i in chosen[l]))
                hs = holes_of(frozenset(P), grid)
                for H in comps(hs):
                    ring_h = nbr(H) - H
                    cov_h = sorted({v for c in H for x, v in cover.get(c, ()) if x <= l})
                    border = [var[(x, i)] for x in range(f, l + 1) for i in chosen[x] if cand[x][i][1] & ring_h]
                    s.add_clause(cov_h + [-v for v in border])
                    added += 1
                if added:
                    break
            if not added and not a.r_only:          # extra pockets of the partial ring
                Pk = frozenset(P)
                Rn = required_set(Pk, contact)
                U_all = Pk | set().union(*(cand[k + 1][i][1] for i in chosen[k + 1]))
                pk = holes_of(frozenset(U_all), grid)
                for H in comps(pk):
                    if not (H - Rn):
                        continue                    # only uncovered required cells: already counted
                    ring_h = nbr(H) - H
                    cov_h = sorted({v for c in H for _x, v in cover.get(c, ())})
                    border = [var[(x, i)] for x in levels for i in chosen[x] if cand[x][i][1] & ring_h]
                    if not a.count_pockets:
                        s.add_clause(cov_h + [-v for v in border])
                        added += 1
                        continue
                    key = (frozenset(H), tuple(sorted(border)))
                    if key in pockets_seen:
                        continue                    # already counted by the defect totalizer
                    pockets_seen.add(key)
                    # p_H <= (every border tile chosen AND no tile covers H): the ring around H stays occupied, so
                    # H is exactly an enclosed pocket, and each of its cells joins the official defect union.
                    top += 1
                    p = top
                    add([p] + cov_h + [-v for v in border])
                    new = []
                    for c in H:
                        if c not in ecell:
                            top += 1
                            ecell[c] = top
                            new.append(top)
                        # a required cell is already counted by uvar when uncovered; count it here only if not required
                        add([-p, ecell[c]] + ([rvar[c]] if c in rvar else []))
                    if new:
                        tot.extend(lits=new, ubound=U, top_id=top)
                        top = max(top, tot.top_id)
                        add_all(tot.cnf.clauses[len(tot.cnf.clauses) - tot.nof_new:])
                        assume = [-tot.rhs[U]]
                    added += 1
            if added:
                cuts += added
                if cuts % 100 < added:
                    print(f"  {cuts} cuts ({time.time() - t0:.0f}s)", flush=True)
                continue
            # candidate found: official re-check
            placements = list(fixed) + [(l, cand[l][i][0]) for l in range(f, k + 1) for i in chosen[l]]
            cor = check_corona(shape, placements, grid, contact, hole_mode="hc")
            R = required_set(cor.patch_cells, contact)
            block = DefectBlock(level=k + 1, u_hc=10**6, u_hh=10**6, required=len(R),
                                tiles=tuple((k + 1, cand[k + 1][i][0]) for i in chosen[k + 1]))
            res = verify_defect(shape, grid, cor, block, contact)
            score = k + float(Fraction(len(R) - res.defect_hc, len(R)))
            if a.count_pockets and (res.defect_hc > U or len(R) < RMIN):
                print(f"\nENCODING MISMATCH: model claims defect <= {U}, |R| >= {RMIN}; official says "
                      f"defect_hc={res.defect_hc}, |R|={len(R)}. Do not trust UNSAT answers from this build.")
                return 2
            print(f"\nSAT after {cuts} cuts ({time.time() - t0:.0f}s). OFFICIAL: coronas={cor.max_level}, "
                  f"defect_hc={res.defect_hc} (hh={res.defect_hh}, pockets={res.pocket_cells}) of {res.required} "
                  f"-> score {score:.6f}")
            if exp:
                export(assume, "SAT", model=model_now)
            if a.out:
                hdr = text.splitlines()[0]
                body = [hdr, f"~ {k} {k} 1", str(len(placements))]
                body += [f"{lvl} {xf.as_text()}" for lvl, xf in zip(cor.levels, (xf for _l, xf in placements))]
                body += [f"#DEFECT {k + 1} {res.defect_hc} {res.defect_hh} {res.required}", str(len(chosen[k + 1]))]
                body += [f"{k + 1} {cand[k + 1][i][0].as_text()}" for i in chosen[k + 1]]
                a.out.write_text("\n".join(body) + "\n", encoding="utf-8")
                print(f"wrote {a.out}")
            return 0
    print("cut budget exhausted")
    return 2


if __name__ == "__main__":
    sys.exit(main())
