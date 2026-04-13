#!/bin/bash
# Solve all AvalonLogs games — sequential (cpus=1) or 2-worker (cpus>1).
# Sequential rate: ~0.6/s. With 2 workers: ~1.2/s.
# Remaining ~3600 files @ 1.2/s ≈ 50 min — fits comfortably in 1-hour test limit.

set -e
cd /home/user

echo "=== CSP4SDG: Solve remaining games + update scores ==="
echo "Start: $(date)"

# --- Step 1: Solve remaining games ---
python3 << 'PYEOF'
import sys, json, time
from pathlib import Path
from multiprocessing import Process

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

all_files = sorted(in_dir.glob("*_constraints.json"))
dst_stems = set(f.stem for f in out_dir.glob("*_solve.json"))
unsolved = [f for f in all_files if f.stem not in dst_stems]

print(f"Total: {len(all_files)} files, {len(dst_stems)} done, {len(unsolved)} to solve")

# Detect worker count: use 2 if multiprocessing can get >1 core
import multiprocessing as mp
n_cores = mp.cpu_count()
# Check effective parallelism
import os
sched_cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else mp.cpu_count()
print(f"Available cores: {sched_cpus}, mp.cpu_count: {n_cores}")

# Use 2 workers if we have >1 effective core, else 1
N_WORKERS = 2 if sched_cpus > 1 else 1
print(f"Workers: {N_WORKERS}")

chunk_size = (len(unsolved) + N_WORKERS - 1) // N_WORKERS

def worker(worker_id, files):
    t0 = time.time()
    solved = errors = 0
    for fp in files:
        dst = out_dir / (fp.stem + "_solve.json")
        try:
            result = solve_one(fp, settings=QUICK_SETTINGS)
            dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
            solved += 1
            if solved % 50 == 0:
                elapsed = time.time() - t0
                rate = solved / elapsed if elapsed > 0 else 0
                print(f"Worker {worker_id}: {solved}/{len(files)} ({rate:.1f}/s)", flush=True)
        except Exception as e:
            errors += 1
            print(f"Worker {worker_id} ERROR {fp.name}: {e}", flush=True)
    elapsed = time.time() - t0
    rate = solved / elapsed if elapsed > 0 else 0
    print(f"Worker {worker_id}: done. {solved} solved, {errors} errors in {elapsed:.0f}s ({rate:.1f}/s)", flush=True)

if N_WORKERS == 1:
    worker(0, unsolved)
else:
    procs = []
    t0 = time.time()
    for i in range(N_WORKERS):
        start = i * chunk_size
        end = min(start + chunk_size, len(unsolved))
        batch = unsolved[start:end]
        p = Process(target=worker, args=(i, batch))
        p.start()
        procs.append(p)
        print(f"Worker {i}: files {start}-{end-1} ({len(batch)} files)", flush=True)
    for p in procs:
        p.join()
    print(f"All workers finished in {time.time() - t0:.0f}s")

n_solved = len(list(out_dir.glob("*_solve.json")))
print(f"Total solved: {n_solved}")
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
PYEOF

echo "=== Complete at $(date) ==="
