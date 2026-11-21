#!/usr/bin/env python3
"""Compare the grouped CSP4SDG solver with literal role-level enumeration.

python3 redteam/iter11/check_enumeration.py <train_instances.json> <out.json>
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from method.csp4sdg_avalonlogs import solve_instance  # noqa: E402
from method.csp4sdg_enumerate import solve_instance_enumerate  # noqa: E402

LIMIT = {5: 60, 6: 60, 7: 40, 8: 20, 9: 8, 10: 3}


def main():
    insts = json.loads(Path(sys.argv[1]).read_text())["instances"]
    seen, maxd, t0 = {}, 0.0, time.time()
    by_view = {}
    for inst in sorted(insts, key=lambda x: x["instance_id"]):
        n = inst["n_players"]
        if seen.get(n, 0) >= LIMIT[n]:
            continue
        seen[n] = seen.get(n, 0) + 1
        a, b = solve_instance(inst), solve_instance_enumerate(inst)
        d = 0.0
        for s in ("CSP_Strict", "CSP_HypIG"):
            for p in inst["players"]:
                pa, pb = a[s]["posterior"][p], b[s]["posterior"][p]
                for r in set(pa) | set(pb):
                    d = max(d, abs(pa.get(r, 0.0) - pb.get(r, 0.0)))
        maxd = max(maxd, d)
        v = inst["view"]["perspective"]
        by_view[v] = by_view.get(v, 0) + 1
    out = {"instances_checked_by_size": seen, "instances_checked_by_view": by_view,
           "max_abs_posterior_difference": maxd, "seconds": round(time.time() - t0, 1)}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=2))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
