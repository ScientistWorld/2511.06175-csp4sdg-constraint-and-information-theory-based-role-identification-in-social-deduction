#!/usr/bin/env python3
"""Role-count prior baseline: every player gets role r with probability count(r)/n.

    python3 baseline/prior.py <input_dir> <output_dir>

Ignores the game history and the viewpoint's private information. Writes the
gym prediction format under the method name "Prior".
"""

import json
import sys
from pathlib import Path


def main():
    inp, out = Path(sys.argv[1]), Path(sys.argv[2])
    instances = json.loads((inp / "instances.json").read_text())["instances"]
    preds = {}
    for inst in instances:
        counts = {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}
        players = inst["players"]
        n = len(players)
        roles = [r for r in sorted(counts) for _ in range(counts[r])]
        preds[inst["instance_id"]] = {"Prior": {
            "posterior": {p: {r: c / n for r, c in counts.items()} for p in players},
            "best": dict(zip(players, roles)),
        }}
    out.mkdir(parents=True, exist_ok=True)
    (out / "predictions.json").write_text(json.dumps({"predictions": preds}))


if __name__ == "__main__":
    main()
