"""Which lazy cut excludes the leader? Evaluate every generated cut against the leader's own x/y."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import joint_opt  # noqa: E402
from heesch_verify.parse import parse_submission  # noqa: E402
from heesch_verify.patch import check_corona  # noqa: E402

text = Path(sys.argv[1]).read_text(encoding="utf-8")
sub = parse_submission(text)
grid, shape = sub.grid, frozenset(sub.cells)
contact = grid.contact(joint_opt.CONTACT_MODE)
base = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
k = base.max_level
LEAD_X = {frozenset(xf.apply_all(shape)) for (lvl, xf), L in zip(sub.patches[0], base.levels) if L == k}
LEAD_Y = {frozenset(xf.apply_all(shape)) for _l, xf in sub.defect.tiles}

src = Path(joint_opt.__file__).read_text(encoding="utf-8")
anchor = "            w.append(cover_h + [-v for v in border])\n"
assert src.count(anchor) == 1
probe = anchor + (
    "            _lx = {xv(i) for i in range(nx) if xcells[i] in LEAD_X}\n"
    "            _ly = {yv(j) for j in range(ny) if ycells[j] in LEAD_Y}\n"
    "            _lead = _lx | _ly\n"
    "            _cl = cover_h + [-v for v in border]\n"
    "            _sat = any((l > 0 and l in _lead) or (l < 0 and -l not in _lead) for l in _cl)\n"
    "            if not _sat:\n"
    "                _kind = 'HOLE' if holes else 'POCKET'\n"
    "                _bcells = ring_h\n"
    "                _occ_lead = set().union(*(xcells[i] for i in range(nx) if xcells[i] in LEAD_X)) | "
    "set().union(*(ycells[j] for j in range(ny) if ycells[j] in LEAD_Y)) | set(Pp)\n"
    "                print(f'!!! UNSOUND CUT #{cuts}: {_kind} |H|={len(H)} cover={len(cover_h)} border={len(border)}; '\n"
    "                      f'H cells covered by leader: {len(H & _occ_lead)}; ring_h cells: {len(_bcells)}; '\n"
    "                      f'ring_h cells EMPTY in leader: {len(_bcells - _occ_lead)}; '\n"
    "                      f'ring_h cells in P_(k-1): {len(_bcells & set(Pp))}; H cells: {sorted(H)[:6]}')\n"
)
src = src.replace(anchor, probe)
ns = {"__name__": "jo_audit", "__file__": joint_opt.__file__, "LEAD_X": LEAD_X, "LEAD_Y": LEAD_Y}
exec(compile(src, joint_opt.__file__, "exec"), ns)
sys.argv = ["joint_opt", sys.argv[1], "--decide", "3/254", "--max-cuts", "60"]
ns["main"]()
