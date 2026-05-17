#!/bin/bash
# Run the paper's proposed CSP4SDG method.
#
# This script:
#   1. Preprocesses AvalonLogs raw data to CSP constraints
#   2. Runs the CSP solver on constraints
#   3. Evaluates results
#
# Usage:
#   bash scripts/method.sh [sample_count]
#     sample_count — Optional: randomly sample N games (for quick test)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SAMPLE_COUNT="${1:-}"

echo "=== CSP4SDG Method Pipeline ==="

# Step 1: Convert raw AvalonLogs to CSP constraints
echo "[1/4] Converting raw AvalonLogs to CSP constraints..."
mkdir -p data/avalonlogs_constraints
python3 -c "
import os
import sys
sys.path.insert(0, os.getcwd())
from data.convert_avalonlogs import main as convert_main
import sys
args = ['convert_avalonlogs.py',
        'data/downloads/avalonlogs_raw',
        'data/avalonlogs_constraints']
"
# Build args manually to avoid sys.argv issues
METHOD_SAMPLE_COUNT="$SAMPLE_COUNT" python3 << 'PYEOF'
import os
import sys
sys.path.insert(0, os.getcwd())
from data.convert_avalonlogs import convert_file
from pathlib import Path
import random
import os

raw_dir = Path("data/downloads/avalonlogs_raw")
out_dir = Path("data/avalonlogs_constraints")
out_dir.mkdir(parents=True, exist_ok=True)

files = [fp for fp in raw_dir.iterdir() if fp.is_file()]
rng = random.Random(42)

sample_count = None
# Check if we should sample
sample_arg = os.environ.get("METHOD_SAMPLE_COUNT", "")
if sample_arg:
    try:
        sample_count = int(sample_arg)
        files = rng.sample(files, min(sample_count, len(files)))
        print(f"Sampling {len(files)} files...")
    except ValueError:
        pass

converted = 0
for fp in files:
    if (out_dir / (fp.stem + "_constraints.json")).exists():
        continue
    result = convert_file(fp)
    if result is None:
        continue
    dst = out_dir / (fp.stem + "_constraints.json")
    import json
    dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
    converted += 1
    if converted % 1000 == 0:
        print(f"  Converted {converted}...")
print(f"Converted {converted} files -> {out_dir}")
PYEOF

# Step 2: Run CSP solver
echo "[2/4] Running CSP solver..."
mkdir -p data/avalonlogs_solve
python3 << 'PYEOF'
import os
import sys
sys.path.insert(0, os.getcwd())
from method.avalon_logs_solver import solve_one
from pathlib import Path

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

files = sorted(in_dir.glob("*_constraints.json"))
sample_arg = "$SAMPLE_COUNT"
if sample_arg:
    import random
    try:
        sample_count = int(sample_arg)
        rng = random.Random(42)
        files = rng.sample(files, min(sample_count, len(files)))
        print(f"Sampling {len(files)} constraint files for solving...")
    except ValueError:
        pass
print(f"Processing {len(files)} constraint files...")

solved = 0
errors = 0
for fp in files:
    dst = out_dir / (fp.stem + "_solve.json")
    if dst.exists():
        solved += 1
        continue
    try:
        result = solve_one(fp)
        import json
        dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
        solved += 1
        if solved % 500 == 0:
            print(f"  Solved {solved}/{len(files)}...")
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ERROR {fp.name}: {e}")

print(f"Solved {solved} files ({errors} errors) -> {out_dir}")
PYEOF

# Step 3: Evaluate
echo "[3/4] Evaluating results..."
bash scripts/evaluate.sh avalonlogs data/avalonlogs_solve scoring/scores.json

# Step 4: Compare with reference
echo "[4/4] Comparing with reference..."
python3 << 'PYEOF'
import json
from pathlib import Path

ref_path = Path("scoring/reference.json")
score_path = Path("scoring/scores.json")

if not score_path.exists():
    print("ERROR: scores.json not found!")
    sys.exit(1)

with open(ref_path) as f:
    ref = json.load(f)
with open(score_path) as f:
    scores = json.load(f)

print("\n=== Comparison: Paper vs Reproduced ===")
for exp_name, exp in scores.get("experiments", {}).items():
    if exp_name not in ref["experiments"]:
        continue
    print(f"\n{exp_name}:")
    ref_exp = ref["experiments"][exp_name]
    for method, vals in exp.get("results", {}).items():
        if method in ref_exp["results"]:
            ref_vals = ref_exp["results"][method]
            primary = ref_exp.get("primary_metric", "")
            if primary and primary in vals and primary in ref_vals:
                rep = vals[primary]
                pap = ref_vals[primary]
                diff = rep - pap
                print(f"  {method}: reproduced={rep:.4f} paper={pap:.4f} diff={diff:+.4f}")
PYEOF

echo "=== Method pipeline complete ==="
