#!/bin/bash
# Solve remaining AvalonLogs games and update scores (PARALLELIZED).
# ~4305 games remaining (8089 solved, 12394 total).
# Settings: Strict + HypIG (QUICK_SETTINGS).
# Uses multiprocessing to parallelize across all CPU cores.

set -e
cd /home/user

echo "=== CSP4SDG: Parallel solve remaining games + update scores ==="
echo "Start: $(date)"
echo "CPUs: $(python3 -c 'import multiprocessing; print(multiprocessing.cpu_count())')"

# --- Step 1: Solve remaining games in parallel ---
python3 << 'PYEOF'
import sys, json, time, os
from pathlib import Path
from multiprocessing import Pool, cpu_count

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

def solve_file(fp_str):
    """Solve a single file. Returns (fp_str, result_str or None, error)."""
    fp = Path(fp_str)
    dst = out_dir / (fp.stem + "_solve.json")
    if dst.exists():
        return (str(fp), None, "skipped")
    try:
        result = solve_one(fp, settings=QUICK_SETTINGS)
        return (str(fp), json.dumps(result, indent=2), None)
    except Exception as e:
        return (str(fp), None, str(e))

# Find all unsolved files
files = [str(fp) for fp in in_dir.glob("*_constraints.json")]
dst_files = set(f.stem for f in out_dir.glob("*_solve.json"))
unsolved = [f for f in files if Path(f).stem not in dst_files]

print(f"Total: {len(files)} files, {len(dst_files)} already solved, {len(unsolved)} to solve")

if unsolved:
    n_workers = cpu_count()
    print(f"Solving {len(unsolved)} files with {n_workers} workers...")

    t0 = time.time()
    solved = skipped = errors = 0
    errors_list = []

    # Process in chunks to update progress
    CHUNK = 200
    for chunk_start in range(0, len(unsolved), CHUNK):
        chunk = unsolved[chunk_start:chunk_start + CHUNK]
        with Pool(n_workers) as pool:
            for (fp_str, result_str, err) in pool.imap_unordered(solve_file, chunk, chunksize=10):
                if err == "skipped":
                    skipped += 1
                elif err:
                    errors += 1
                    if len(errors_list) < 3:
                        errors_list.append(f"  ERROR {Path(fp_str).name}: {err}")
                else:
                    dst = out_dir / (Path(fp_str).stem + "_solve.json")
                    dst.write_text(result_str, encoding="utf-8")
                    solved += 1

        elapsed = time.time() - t0
        rate = solved / elapsed if elapsed > 0 else 0
        remaining = len(unsolved) - solved - skipped - errors
        eta = remaining / rate if rate > 0 else 0
        print(f"  {solved} solved, {skipped} skip, {errors} err, {remaining} remain, {rate:.1f}/s, ETA: {eta/60:.0f}m")

    elapsed = time.time() - t0
    print(f"Solve done. Solved: {solved}, Skipped: {skipped}, Errors: {errors} in {elapsed/60:.1f}m ({solved/elapsed*60:.0f}/min)")
    for e in errors_list:
        print(e)
else:
    print("All files already solved.")
PYEOF

# --- Step 2: Update scores.json ---
python3 << 'PYEOF'
import json, re
from pathlib import Path
from collections import defaultdict

results_dir = Path("data/avalonlogs_solve")
score_path = Path("scoring/scores.json")

def canon(v):
    v2 = v.lower()
    stripped = re.sub(r'\d+$', '', v2)
    if stripped in ("merlin",): return "MRL"
    if stripped in ("percival",): return "PCV"
    if stripped in ("morgana",): return "MRG"
    if stripped in ("servant", "loyal_follower", "loyal_servant"): return "LSV"
    if stripped in ("assassin",): return "ASN"
    if stripped in ("evil_minion", "evil-minion", "mordred", "oberon"): return "EVM"
    if stripped in ("objective",): return "Obj"
    return stripped

VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM"}
SIZE_TO_EXP = {5: "avalonlogs_5player", 6: "avalonlogs_6player",
               7: "avalonlogs_7player", 8: "avalonlogs_8player",
               9: "avalonlogs_9player", 10: "avalonlogs_10player"}

by_size = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for fp in sorted(results_dir.glob("*_solve.json")):
    try:
        game = json.loads(fp.read_text())
    except:
        continue
    truth = game.get("players", {})
    n_players = len(truth)
    if n_players == 0:
        continue
    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            cv = canon(view)
            if cv in ("unknown", "obj") and view.lower() != "objective":
                continue
            for setting, data in settings.items():
                post = data.get("posterior", {})
                if not post:
                    continue
                marg = sum(post.get(p, {}).get(r, 0.0) for p, r in truth.items()) / n_players
                by_size[n_players][setting][cv].append(marg)

scores = {"experiments": {}, "metadata": {"dataset": "avalonlogs", "condition": "Truth"}}

for size, settings_data in sorted(by_size.items()):
    exp_name = SIZE_TO_EXP.get(size)
    if exp_name is None:
        continue
    scores["experiments"][exp_name] = {"results": {}}
    for setting, views_data in sorted(settings_data.items()):
        setting_clean = setting.replace("+", "")
        mname = f"CSP_{setting_clean}"
        scores["experiments"][exp_name]["results"][mname] = {}
        for view, vals in views_data.items():
            if view not in VALID_VIEWS or not vals:
                continue
            avg_marg = round(sum(vals) / len(vals), 4)
            scores["experiments"][exp_name]["results"][mname][f"{view}_marginal"] = avg_marg
        obj_marg = by_size[size].get("Strict", {}).get("Obj", [])
        if obj_marg:
            obj_avg = round(sum(obj_marg) / len(obj_marg), 4)
            scores["experiments"][exp_name]["results"][mname]["Obj_marginal"] = obj_avg

with open(score_path, "w") as f:
    json.dump(scores, f, indent=2)

print(f"Scores updated: {list(scores['experiments'].keys())}")
for exp, data in sorted(scores["experiments"].items()):
    for mname, vals in sorted(data["results"].items()):
        marginals = {k: round(v, 3) for k, v in vals.items() if k.endswith("_marginal")}
        print(f"  {exp} / {mname}: {marginals}")

for size in sorted(SIZE_TO_EXP.keys()):
    count = 0
    for fp in results_dir.glob("*_solve.json"):
        try:
            if len(json.loads(fp.read_text()).get("players", {})) == size:
                count += 1
        except:
            pass
    print(f"  {size}-player: {count} games solved")
PYEOF

echo "=== Complete at $(date) ==="
