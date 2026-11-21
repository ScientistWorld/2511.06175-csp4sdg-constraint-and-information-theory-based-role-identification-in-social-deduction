#!/bin/bash
# Run the paper's CSP4SDG method (method/csp4sdg_avalonlogs.py, via
# scripts/predict.sh) on the visible train instances, write scoring/scores.json
# and print the reproduced marginal accuracy next to the paper's numbers.
#
#   bash scripts/method.sh [--limit-per-size N]
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

bash scripts/evaluate.sh "$@"

python3 - <<'PYEOF'
import json
ref = json.load(open("scoring/reference.json"))["experiments"]
sc = json.load(open("scoring/scores.json"))["experiments"]
for exp in sorted(sc, key=lambda e: int(e.split("_")[1].replace("player", ""))):
    print(f"\n{exp}")
    for m, vals in sc[exp]["results"].items():
        paper = ref.get(exp, {}).get("results", {}).get(m, {})
        cells = []
        for v in ("Obj", "MRL", "PCV", "MRG", "LSV", "EVM"):
            p = paper.get(f"{v}_marginal")
            cells.append(f"{v} {vals[f'{v}_marginal']:.3f}" + (f" (paper {p:.3f})" if p is not None else "")
                         + f" brier {vals[f'{v}_brier']:.3f}")
        print(f"  {m}: " + "; ".join(cells))
PYEOF
