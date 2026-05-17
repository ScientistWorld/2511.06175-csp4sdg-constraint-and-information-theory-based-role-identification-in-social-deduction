#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# scripts/baseline.sh and scripts/method.sh to run baselines and
# the paper's method, each of which calls scripts/evaluate.sh.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is the repository root
#
# This is the "gold standard" reproduction —
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== CSP4SDG Full Reproduction Pipeline ==="

# Step 1: Download data (if not already present)
echo "[1/5] Ensuring data is available..."
bash scripts/download.sh

# Step 2: Baseline note
echo "[2/5] Skipping optional LLM baselines; this reproduction is self-contained and evaluates CSP-only AvalonLogs results."

# Step 3: Run the paper's method
echo "[3/5] Running CSP4SDG method (full dataset)..."
bash scripts/method.sh

# Step 4: Validate scores
echo "[4/5] Validating results..."
python3 << 'PYEOF'
import json
from pathlib import Path

ref_path = Path("scoring/reference.json")
score_path = Path("scoring/scores.json")

with open(ref_path) as f:
    ref = json.load(f)
with open(score_path) as f:
    scores = json.load(f)

print("\n=== Final Results Summary ===")
for exp_name, exp in scores.get("experiments", {}).items():
    if exp_name not in ref["experiments"]:
        continue
    ref_exp = ref["experiments"][exp_name]
    primary = ref_exp.get("primary_metric", "")
    print(f"\n{exp_name}:")
    for method, vals in exp.get("results", {}).items():
        if method in ref_exp["results"]:
            ref_vals = ref_exp["results"][method]
            if primary and primary in vals and primary in ref_vals:
                rep = vals[primary]
                pap = ref_vals[primary]
                diff = rep - pap
                marker = "✓" if abs(diff) < 0.1 else "⚠"
                print(f"  {marker} {method}: reproduced={rep:.4f} paper={pap:.4f} diff={diff:+.4f}")

print("\n=== Reproduction Complete ===")
PYEOF

# Step 5: Show output paths
echo "[5/5] Output files:"
echo "  Scores: scoring/scores.json"
echo "  CSP results: data/avalonlogs_solve/"
echo "  Baseline results: data/avalonlogs_baseline_random/"
