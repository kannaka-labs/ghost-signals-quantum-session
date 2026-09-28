"""Official defect numbers for a submission's own #DEFECT block, plus a direct check of one cell."""
import sys
from pathlib import Path

from heesch_verify.defect import verify_defect
from heesch_verify.parse import parse_submission
from heesch_verify.patch import check_corona
from heesch_verify.shape import holes_of

sub = parse_submission(Path(sys.argv[1]).read_text(encoding="utf-8"))
grid, shape = sub.grid, frozenset(sub.cells)
contact = grid.contact("point")
cor = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
res = verify_defect(shape, grid, cor, sub.defect, contact)
print(f"official: defect_hc={res.defect_hc} defect_hh={res.defect_hh} pockets={res.pocket_cells} required={res.required}")
covered = set().union(*(xf.apply_all(shape) for _l, xf in sub.defect.tiles))
U = frozenset(cor.patch_cells | covered)
pk = holes_of(U, grid)
print(f"pockets by flood fill: {len(pk)} {sorted(pk)[:8]}")
for c in [tuple(int(v) for v in s.split(',')) for s in sys.argv[2:]]:
    nb = contact.neighbors(c)
    print(f"cell {c}: in U? {c in U}; neighbours occupied {sum(n in U for n in nb)}/{len(nb)}; in pocket set? {c in pk}")
