"""Export the leader's corona geometry as JSON for the report figure (official parse + check_corona + verify_defect)."""
import json
import sys
from pathlib import Path

from heesch_verify.defect import verify_defect
from heesch_verify.parse import parse_submission
from heesch_verify.patch import check_corona, required_set

sub = parse_submission(Path(sys.argv[1]).read_text(encoding="utf-8"))
grid, shape = sub.grid, frozenset(sub.cells)
contact = grid.contact("point")
cor = check_corona(shape, sub.patches[0], grid, contact, hole_mode="hc")
res = verify_defect(shape, grid, cor, sub.defect, contact)
R = required_set(cor.patch_cells, contact)
partial = set().union(*(xf.apply_all(shape) for _l, xf in sub.defect.tiles))
tiles = [{"level": int(l), "cells": sorted(list(c) for c in cells)} for l, cells in zip(cor.levels, cor.tile_cells)]
tiles += [{"level": 5, "cells": sorted(list(c) for c in xf.apply_all(shape))} for _l, xf in sub.defect.tiles]
out = {
    "grid": sub.grid_id, "shape_cells": len(shape), "coronas": cor.max_level,
    "required": res.required, "uncovered": sorted(list(c) for c in (R - partial)),
    "defect_hc": res.defect_hc, "tiles": tiles,
}
Path(sys.argv[2]).write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"tiles={len(tiles)} required={res.required} uncovered={out['uncovered']} defect={res.defect_hc}")
