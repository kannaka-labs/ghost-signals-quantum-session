"""Why does --decide reject the leader's own configuration? Pin it as assumptions and bisect."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import joint_opt  # noqa: E402

from pysat.solvers import Solver  # noqa: E402
from heesch_verify.parse import parse_submission  # noqa: E402
from heesch_verify.patch import check_corona, required_set  # noqa: E402

CAPTURE = {}


class Capture(Exception):
    pass


orig_solver = None


def run(decide):
    # Monkeypatch Solver inside joint_opt's decide branch: grab the formula and the
    # variable maps instead of solving.
    import pysat.solvers as ps

    class Grab:
        def __init__(self, name, bootstrap_with):
            CAPTURE["hard"] = [list(c) for c in bootstrap_with]
            raise Capture()
    real = ps.Solver
    ps.Solver = Grab
    sys.argv = ["joint_opt", sys.argv[1], "--decide", decide]
    try:
        joint_opt.main()
    except Capture:
        pass
    finally:
        ps.Solver = real


# Recreate the variable maps exactly as joint_opt does, by re-running its setup with a
# capture of locals via a light instrumented copy: simplest is to rebuild the leader's
# cell sets and match them against joint_opt's printed universes. Instead we recompute
# the two tile lists here with the SAME code paths joint_opt uses.
text = Path(sys.argv[1]).read_text(encoding="utf-8")
sub = parse_submission(text)
grid, shape = sub.grid, frozenset(sub.cells)
contact = grid.contact(joint_opt.CONTACT_MODE)
base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
k = base.max_level
lead_x = [frozenset(xf.apply_all(shape)) for (lvl, xf), L in zip(sub.patches[0], base.levels) if L == k]
lead_y = [frozenset(xf.apply_all(shape)) for _l, xf in sub.defect.tiles]
print(f"leader: ring{k} {len(lead_x)} tiles, ring{k + 1} {len(lead_y)} tiles, |R|={len(required_set(base.patch_cells, contact))}")

# Instrument joint_opt: expose xcells/ycells/rvar/uvar via a global hook.
src = Path(joint_opt.__file__).read_text(encoding="utf-8")
hook = "    print(f\"band cells {len(band)}, clauses {len(w.hard)} hard / {len(w.soft)} soft\")"
assert src.count(hook) == 1
src = src.replace(hook, hook + "\n    globals()['DBG'] = dict(xcells=xcells, ycells=ycells, rvar=rvar, uvar=uvar, nx=nx, ny=ny, band=band)")
ns = {"__name__": "jo_dbg", "__file__": joint_opt.__file__}
exec(compile(src, joint_opt.__file__, "exec"), ns)

import pysat.solvers as ps  # noqa: E402


class Grab:
    def __init__(self, name, bootstrap_with):
        CAPTURE["hard"] = [list(c) for c in bootstrap_with]
        raise Capture()


real = ps.Solver
ps.Solver = Grab
sys.argv = ["joint_opt", sys.argv[1], "--decide", "3/254"]
try:
    ns["main"]()
except Capture:
    pass
finally:
    ps.Solver = real
D = ns["DBG"]
xidx = {cs: i for i, cs in enumerate(D["xcells"])}
yidx = {cs: j for j, cs in enumerate(D["ycells"])}
miss_x = [cs for cs in lead_x if cs not in xidx]
miss_y = [cs for cs in lead_y if cs not in yidx]
print(f"leader ring{k} tiles missing from X universe: {len(miss_x)}; ring{k + 1} tiles missing from Y: {len(miss_y)}")
if miss_y:
    Pp = frozenset().union(*(base.level_cells[i] for i in range(k)))
    nbr = lambda cells: {n for c in cells for n in contact.neighbors(c)}  # noqa: E731
    for cs in miss_y[:3]:
        print("   missing y: overlaps P_{k-1}?", bool(cs & Pp), " touches P_{k-1}?", bool(nbr(cs) & Pp))
nx, ny = D["nx"], D["ny"]
chosen_x = {xidx[cs] for cs in lead_x if cs in xidx}
chosen_y = {yidx[cs] for cs in lead_y if cs in yidx}
assum = [(i + 1) if i in chosen_x else -(i + 1) for i in range(nx)]
assum += [(nx + j + 1) if j in chosen_y else -(nx + j + 1) for j in range(ny)]
hard = CAPTURE["hard"]
with real(name="cadical153", bootstrap_with=hard) as s:
    ok = s.solve(assumptions=assum)
    print(f"full --decide 3/254 formula with the leader pinned: {'SAT' if ok else 'UNSAT'}")
    if ok:
        m = set(l for l in s.get_model() if l > 0)
        print("  r true:", sum(1 for v in D["rvar"].values() if v in m), " u true:", sum(1 for v in D["uvar"].values() if v in m))
