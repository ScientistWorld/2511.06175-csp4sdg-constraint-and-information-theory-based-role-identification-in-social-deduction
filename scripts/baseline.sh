#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines implemented:
#   - random: Random role assignment based on role priors
#   - prior: Prior probability assignment (all players get uniform prior)
#
# Usage:
#   bash scripts/baseline.sh random [results_dir]
#   bash scripts/baseline.sh prior [results_dir]

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

METHOD="${1:-random}"
RESULTS_DIR="${2:-data/avalonlogs_baseline_${METHOD}}"

mkdir -p "$RESULTS_DIR"

echo "=== Running baseline: $METHOD ==="

python3 << PYEOF
import os
import sys
sys.path.insert(0, os.getcwd())
import json
import random
from pathlib import Path
from collections import Counter
import itertools
import math

def random_baseline(constraints_path: Path, out_path: Path):
    """Random baseline: assigns roles uniformly at random from feasible worlds."""
    with open(constraints_path, encoding='utf-8') as f:
        game = json.load(f)

    truth = {p["name"]: p["role"] for p in game["players"]}
    schema_data = game["schema"]
    players = [p["name"] for p in game["players"]]

    # Build role counts
    role_counts = schema_data["role_counts"]
    good_roles = set(schema_data["good_roles"])

    # Enumerate all assignments
    items = list(role_counts.items())
    def rec(i, remaining, part):
        if i == len(items):
            yield dict(part)
            return
        role, k = items[i]
        for combo in itertools.combinations(remaining, k):
            nxt_rem = [p for p in remaining if p not in combo]
            nxt_part = dict(part)
            for p in combo:
                nxt_part[p] = role
            yield from rec(i + 1, nxt_rem, nxt_part)

    worlds = list(rec(0, players, {}))
    n_worlds = len(worlds)

    # Compute uniform marginal (each world equally likely)
    marginal = {p: Counter() for p in players}
    for w in worlds:
        for p, r in w.items():
            marginal[p][r] += 1
    for p in players:
        for r in marginal[p]:
            marginal[p][r] /= n_worlds

    # Random MAP: pick one world uniformly at random
    rng = random.Random(42)
    random_world = rng.choice(worlds)

    out = {
        "file": constraints_path.name,
        "players": truth,
        "quests": {}
    }

    for q in game["quests"]:
        idx = q["quest"]
        out["quests"][str(idx)] = {}
        for view in ["objective", "merlin", "percival", "morgana", "servant",
                     "loyal_follower", "assassin", "evil_minion"]:
            out["quests"][str(idx)][view] = {
                "Strict": {
                    "posterior": {p: dict(marginal[p]) for p in players},
                    "best": random_world
                }
            }

    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def prior_baseline(constraints_path: Path, out_path: Path):
    """Prior baseline: each player gets uniform probability over all roles."""
    with open(constraints_path, encoding='utf-8') as f:
        game = json.load(f)

    truth = {p["name"]: p["role"] for p in game["players"]}
    players = [p["name"] for p in game["players"]]
    role_counts = game["schema"]["role_counts"]

    # Uniform prior: each player gets equal probability for each of their possible roles
    all_roles = list(role_counts.keys())
    n_roles = len(all_roles)
    uniform = {r: 1.0 / n_roles for r in all_roles}

    # Random MAP: uniform random assignment
    rng = random.Random(42)
    items = list(role_counts.items())
    def rec(i, remaining, part):
        if i == len(items):
            yield dict(part)
            return
        role, k = items[i]
        for combo in itertools.combinations(remaining, k):
            nxt_rem = [p for p in remaining if p not in combo]
            nxt_part = dict(part)
            for p in combo:
                nxt_part[p] = role
            yield from rec(i + 1, nxt_rem, nxt_part)

    worlds = list(rec(0, players, {}))
    random_world = rng.choice(worlds)

    out = {
        "file": constraints_path.name,
        "players": truth,
        "quests": {}
    }

    for q in game["quests"]:
        idx = q["quest"]
        out["quests"][str(idx)] = {}
        for view in ["objective", "merlin", "percival", "morgana", "servant",
                     "loyal_follower", "assassin", "evil_minion"]:
            out["quests"][str(idx)][view] = {
                "Prior": {
                    "posterior": {p: uniform for p in players},
                    "best": random_world
                }
            }

    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


constraints_dir = Path("data/avalonlogs_constraints")
results_dir = Path("$RESULTS_DIR")
results_dir.mkdir(parents=True, exist_ok=True)

files = list(constraints_dir.glob("*_constraints.json"))
print(f"Running {len(files)} games through {METHOD} baseline...")

for fp in files:
    dst = results_dir / (fp.stem + f"_{METHOD}.json")
    if dst.exists():
        continue
    try:
        if "$METHOD" == "random":
            random_baseline(fp, dst)
        else:
            prior_baseline(fp, dst)
    except Exception as e:
        print(f"ERROR {fp.name}: {e}")

print(f"Baseline '{METHOD}' results -> {results_dir}")
PYEOF

echo "=== Baseline complete ==="
