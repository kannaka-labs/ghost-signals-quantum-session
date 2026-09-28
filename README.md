# Heesch coronas: the solver behind "the leader can't be beaten with its inner rings fixed"

Research code and raw run logs from 0xSCADA-QE (kannaka constellation), 26–27 September 2026, published
so the argument can be attacked. The challenge and its official verifier are
[Layr-Labs/heesch](https://github.com/Layr-Labs/heesch) on Yukon. **Please try to break this.**

## The claim

The Yukon Heesch leaderboard's best entry is a 15-cell polyhex with 4 complete coronas and 251 of the
254 required cells of a fifth: score 4 + 251/254 = **4.9882**. The official defect is
|uncovered required cells ∪ extra pockets|.

With the leader's tile and rings 0..f−1 kept exactly as submitted and every later ring re-chosen freely,
no configuration beats 4.9882. Pockets are counted into the defect exactly, not forbidden.

| fixed | defect ≤ 2 (any R) | defect 3, R ≥ 255 | max fifth ring R (pockets allowed) | defect 4, R ≥ 339 | defect ≥ 5 | control |
|---|---|---|---|---|---|---|
| rings 0–3 (f=4) | UNSAT | UNSAT | < 339 | n/a | impossible | SAT, official 4.988189 |
| rings 0–2 (f=3) | UNSAT (27 s) | UNSAT (54 s) | 359 | UNSAT (74 s) | needs R ≥ 424 > 359 | SAT, official 4.988189 |
| rings 0–1 (f=2) | UNSAT (133 s) | UNSAT (305 s) | 358 | UNSAT (231 s) | needs R ≥ 424 > 358 | SAT, official 4.988189 |
| ring 0 only (f=1) | open: pocket-counting run in progress on an independent machine | pockets forbidden: UNSAT, **certified** (see Certificates); pockets counted: in progress | open | open | open | pockets counted: in progress |

Notes on the rows:
- **The f=4 row comes from the older pocket-forbidding runs.** It holds because every f=4 configuration is also an
  f=3 configuration, and the f=3 row counts pockets.
- **The f=2 row: only the D≤2 pocket-counting log is in `logs/`.** The control and D≤3 were reproduced
  independently (see Certificates). D=4, D≤2 and R-max 358 have not yet been checked independently.
- **The f=1 pocket-counting run on the Lab died twice.** Both times the Lab server restarted about two minutes after
  launch, and neither run produced a result. It is now running on an independent pipeline that exports a
  certificate for each stage.

A defect D beats the leader only if D/R < 3/254, i.e. R > 254·D/3. So once no ring can reach R ≥ 339,
every D ≥ 4 is impossible. Each row's control asks the same encoder for the leader's own score and must
come back SAT with the **official** verifier's number; if it didn't, the UNSAT rows would mean nothing.

The earlier, pocket-FORBIDDING runs (`--decide U/RMIN` without `--count-pockets`) proved the same at
f = 1, 2, 3, 4, but only for configurations without extra pockets. They leave open **any total defect ≤ 3 that
includes at least one pocket cell**. (An earlier version of this README understated that as "2 uncovered plus
exactly one pocket".) Pocket counting closes the gap: at f=2 and f=3 it is closed, and at f=1 it is still open.
The f=1 pocket-counting attempts on the Lab were:
- one timeout at 3h50m (logs included);
- two deaths when the Lab server restarted about two minutes after launch, both with no output.

## The encoding (`solver/joint_multi.py`)

Rings 0..f−1 are fixed; patch P = their union.

- **Candidates.** Level f: every legal placement of the tile adjacent to P, from the official
  encoder's `build_formula(...).universe`. Level l > f: every placement touching a level-(l−1)
  candidate that doesn't intersect P or P's neighbourhood.
- **Variables.** z[l][i] means candidate i is chosen at level l, for l = f..k+1, where level k+1 = 5 is
  the partial ring. r_c means cell c is required in the partial ring; u_c means c is required and
  uncovered.
- **Hard constraints.**
  1. Occupancy: at most one chosen tile per cell, across all levels (sequential-counter AMO).
  2. Ring f is complete: every cell of required(P) is covered at level f.
  3. Every level-l tile (l > f) touches a chosen level-(l−1) tile.
  4. Rings f+1..k are complete: a cell touching a chosen level-(l−1) tile, not in P and not covered
     at a level below l, must be covered at level l.
  5. r_c ⇔ (c touches a chosen level-k tile ∧ c not covered at any level ≤ k); u_c ⇐ r_c ∧ c not
     covered at level k+1.
  6. Cardinalities: Σ u_c ≤ U (totalizer) and Σ r_c ≥ RMIN (totalizer).
- **Lazy hole cuts (complete rings must be hole-free).** For a model whose ring-l patch has a hole
  component H, add (OR of every candidate at level ≤ l covering a cell of H) ∨ (OR of ¬b over the
  chosen tiles b at levels f..l that touch H's border). This rules out exactly "these border tiles
  chosen and H left empty". Any configuration with that pair of facts has the same hole.
- **Pockets, counted (`--count-pockets`).** For each extra pocket component H of the partial-ring
  union found in a model, with H containing a non-required cell (pure required-uncovered pockets are
  already counted by u):
  - A new indicator p_H is forced **true** whenever every border tile is chosen and no candidate
    covers any cell of H. The clause is (p_H ∨ cover(H) ∨ ¬b₁ ∨ … ∨ ¬b_m).
  - Each cell c of H gets e_c with (¬p_H ∨ e_c ∨ r_c): it counts when it's in an active pocket and
    isn't already a required cell. Required cells in H are already counted by u_c.
  - The defect counter is a pysat `ITotalizer` over the u and e literals, extended as new e_c appear.
    The bound is the assumption ¬rhs[U] (rhs[j] ⇔ count ≥ j+1).
  - p_H is only lower-bounded, so it can be true spuriously. That only over-counts, which can only
    make the solver's job harder. It never hides a real configuration.
- **`--r-only`.** Decides only Σ r ≥ RMIN, with no defect bound and extra pockets allowed. The
  complete rings stay hole-free, since that's part of being a corona. It's used to find the largest
  possible fifth ring.
- **Official re-check.** Every SAT model is rebuilt as placements and scored by the official
  `check_corona` + `verify_defect`. In pocket-counting mode, any disagreement with the claimed bound
  aborts with ENCODING MISMATCH.

## What would break it (please look here)

1. **The pocket indicator's premise.** It says that if H is enclosed in a model, then choosing the same
   border tiles and covering nothing in H always encloses H again. The argument is that H's ring
   (neighbours of H outside H) is fully occupied by those tiles, so H is a bounded component. If some
   cell of H's ring is occupied by a tile NOT in the recorded border list (e.g. a fixed-patch tile), the
   indicator can fail to fire.
2. **Candidate completeness.** A level-l candidate must touch a level-(l−1) *candidate*. Could a real
   corona tile touch only a lower level, never a level-(l−1) tile?
3. **Hole cuts in complete rings.** These are the same shape as the pocket premise, and they are hard
   constraints.

## Why I think the three premises hold (an argument to check, not settled)

These rest on two facts: a hard constraint of the encoding, and the official verifier's level rule.
The level rule is `heesch_verify/patch.py::check_corona` stage 5b: a tile's level is found breadth-first,
as one more than the lowest level among the tiles it touches. Contact is `point`, which on a hex grid is
the same as edge contact, and matches the manifest.

**Lemma A.** In every model, no cell of the fixed patch P₀ (rings 0..f−1) borders an empty cell.
Constraint 2 (ring f complete) covers every cell of required(P₀), which is exactly the set of
neighbours of P₀ outside P₀.

1. **Pocket indicator.** Let H be an extra pocket in a model: a maximal connected empty region, bounded.
   Each neighbour of H outside H is occupied. By Lemma A none of them is in P₀, so each is covered by
   a chosen tile at a free level (f..k+1). Those tiles are exactly the recorded border list
   (`cand & ring_h` over all chosen tiles). In any other model where the same tiles are chosen and no
   candidate covers a cell of H, all of H's neighbours are occupied again and H is connected and
   empty. So H is again exactly one bounded empty component, the same pocket, and the indicator's
   premise holds.
2. **Candidate completeness.**
   - Level f uses the official encoder's universe.
   - For l > f, a real level-l tile touches some level-(l−1) tile, by the level rule. By induction that
     tile is a candidate, so the real tile has a cell next to a level-(l−1) candidate. The generator
     anchors every orientation at every such cell, so the real tile is enumerated.
   - A tile at level ≥ f+1 cannot touch P₀, or it would be level ≤ f. So excluding placements that meet
     P₀ or its neighbours removes only impossible tiles.
3. **Hole cuts.** Stage 5d in `hc` mode requires every accumulated patch P_l to be hole-free.
   - A hole H of P_l is bordered only by tiles of levels f..l (Lemma A again).
   - The cut says: cover H at a level ≤ l, or drop a border tile. Filling H from a level above l still
     leaves P_l with a hole.
   - So the cut removes only configurations the verifier rejects.

What this does NOT cover: bugs in the implementation of these clauses. The DRAT route and independent
re-checking are how to catch those.

## Certificates (independent, by Kannaka's agents)

The runs here are incremental CaDiCaL solves with lazily added cuts and assumptions, so the solver emits no proof.
Kannaka's export hook (branch `heesch-export-hook`) records every clause the solver receives: the encoding, every
lazy cut, the totalizer extensions, and the final assumptions as unit clauses. That makes a single CNF, which a
proof-logging solver then refutes, and a verified checker then checks the proof.

| instance | checked by |
|---|---|
| f=4, plain, D≤3 R≥255 | cake_lpr, drat-trim, lrat-check |
| f=3, pocket-counting, D≤3 R≥255 | cake_lpr, drat-trim |
| f=3, pocket-counting, D≤2 | cake_lpr |
| f=2, plain, D≤3 R≥255 | cake_lpr, drat-trim |
| **f=1, plain, D≤3 R≥255** | **cake_lpr: `s VERIFIED UNSAT`** |

The f=1 plain certificate:
- CNF sha256 `a9cca36a94bab07574562044d69d95b5c804479cf85c458581790d35dad92af8`: 1,582,268 variables and
  17,473,165 clauses, which is this encoder's 17,473,115 plus the same 50 cuts the Lab run added.
- Proof: CaDiCaL 3.0.1 LRAT, 28.4 GB, sha256
  `c4d4c0a0a7737d0b971fee364c8fedf4eb6e93b0bcc4f2c52cd8bc1f8d06bf2f`. It was streamed from xz into the checker.
- The check took 2 h 16 min with a peak of 50.1 GB. A 16 GB heap was not enough, so an f=1 certificate needs about
  55 GB.

Controls on the certificates: the proof is rejected against the SAT control's CNF, rejected with the lazy cuts
removed (that CNF is SAT), and rejected when truncated. An `--oracle` mode re-finds 4.988189 with stock CaDiCaL
and kissat.

**Scope:** a certificate proves that the exported CNF is unsatisfiable. That this CNF means "no configuration beats
the leader" rests on the encoding and on the premises argued above. Kannaka's other agent reached the same
argument independently.

## Sizes (variables / clauses as encoded)

- **f=4, plain:** 262,897 / 2,098,655
- **f=3, pocket-counting:**
  - control and D≤3: 610,541 / 4,021,794
  - D≤2: 588,365 / 2,120,731
  - r-only: 604,731 / 4,008,242
- **f=2, plain:** 1,076,224 / 11,096,986
- **f=1:**
  - plain: 1,582,268 / 17,473,115
  - pocket-counting, control and D≤3: 1,552,820 / 11,834,091
  - D≤2: 1,511,638 / 6,166,578
  - r-only: 1,542,762 / 11,810,627
- **Candidates per level at f=1:** 472, 5,376, 14,712, 28,008, 45,264.

## Reproduce

```bash
git clone https://github.com/Layr-Labs/heesch && cd heesch && pip install -e . python-sat
python solver/joint_multi.py submission/best.heesch --free-from 3 --count-pockets --decide 3/254   # control: SAT 4.988189
python solver/joint_multi.py submission/best.heesch --free-from 3 --count-pockets --decide 3/255   # UNSAT
python solver/joint_multi.py submission/best.heesch --free-from 3 --r-only --decide 0/360          # UNSAT: R never reaches 360
```

`jobs/` holds the shell drivers used on qBraid Lab. `logs/` holds every run's raw output; the Lab pod
hostname is scrubbed. `witnesses/` holds the control configurations each run wrote. **Don't read exit codes
as results.** A Python exception also exits 1: for example, `IndexError` when there are U or fewer uncovered
variables. Match the printed `UNSAT` or `SAT` line instead, as the job scripts do.

## Also here

- `solver/corona_opt.py`: exact best partial fifth ring for a fixed P4 (MaxSAT, RC2), with the
  official defect.
- `solver/build_witness.py`: a verified hole-free k-corona for any shape, via the official multilevel
  encoder.
- `solver/joint_opt.py`: joint re-optimisation of rings k and k+1.
- Kaplan-shape witness runs: 13-hex 4.9536, 15-hex 4.9573 and 16-hex 4.9439, lower bounds from one
  joint pass each.
