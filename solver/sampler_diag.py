"""Why do sampled rings fail check_corona? Tally the verifier's error codes."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corona_sampler import to_xform  # noqa: E402
from corona_opt import CONTACT_MODE  # noqa: E402
from heesch_encoder.clauses import build_formula  # noqa: E402
from heesch_verify.parse import parse_submission  # noqa: E402
from heesch_verify.patch import check_corona  # noqa: E402
from heesch_verify.result import VerifyError  # noqa: E402
from pysat.solvers import Solver  # noqa: E402

sub = parse_submission(Path(sys.argv[1]).read_text(encoding="utf-8"))
grid, shape = sub.grid, frozenset(sub.cells)
contact = grid.contact(CONTACT_MODE)
base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
k = base.max_level
inner = [pl for pl, lvl in zip(sub.patches[0], base.levels) if lvl < k]
P_prev = frozenset().union(*(base.level_cells[i] for i in range(k)))
# control: the leader's OWN ring must be a model of this formula and pass
own = [pl for pl, lvl in zip(sub.patches[0], base.levels) if lvl == k]
f = build_formula(shape, P_prev, grid, contact)
tally = collections.Counter()
with Solver(name="cadical153", bootstrap_with=[list(c) for c in f.clauses]) as s:
    for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 60):
        if not s.solve():
            break
        m = s.get_model()
        chosen = [v for v in range(1, len(f.universe) + 1) if m[v - 1] > 0]
        s.add_clause([-v for v in chosen])
        ring = [(k, to_xform(grid, f.universe[v - 1])) for v in chosen]
        try:
            c = check_corona(shape, list(inner) + ring, grid, contact, hole_mode="hc")
            tally["OK" if c.max_level == k else f"max_level={c.max_level}"] += 1
        except VerifyError as e:
            tally[str(e.code)] += 1
print("own ring (control):", end=" ")
try:
    print("OK" if check_corona(shape, list(inner) + own, grid, contact, hole_mode="hc").max_level == k else "level?")
except VerifyError as e:
    print("FAILS", e.code)
print(dict(tally))
