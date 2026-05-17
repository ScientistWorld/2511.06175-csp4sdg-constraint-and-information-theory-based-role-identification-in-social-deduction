#!/bin/bash
# Resume the AvalonLogs CSP4SDG reproduction.
#
# This CPU job solves only missing AvalonLogs outputs, then refreshes
# scoring/scores.json and validates it against scoring/reference.json.
set -e
cd /home/user

echo "=== CSP4SDG: resume missing AvalonLogs solves ==="
echo "Start: $(date)"

mkdir -p data/avalonlogs_raw data/avalonlogs_constraints data/avalonlogs_solve scoring

echo "[1/4] Ensure raw data is present"
if [ -n "$(find data/avalonlogs_raw -maxdepth 1 -type f -print -quit 2>/dev/null)" ]; then
    echo "AvalonLogs raw data already present: $(find data/avalonlogs_raw -maxdepth 1 -type f | wc -l) files"
else
    bash scripts/download.sh
fi

echo "[2/4] Convert any raw logs missing constraint files"
python3 - <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user")
from data.convert_avalonlogs import convert_file

raw_dir = Path("data/avalonlogs_raw")
out_dir = Path("data/avalonlogs_constraints")
out_dir.mkdir(parents=True, exist_ok=True)

converted = skipped = failed = 0
for fp in sorted(raw_dir.iterdir()):
    if not fp.is_file():
        continue
    dst = out_dir / f"{fp.stem}_constraints.json"
    if dst.exists():
        skipped += 1
        continue
    result = convert_file(fp)
    if result is None:
        failed += 1
        continue
    dst.write_text(json.dumps(result), encoding="utf-8")
    converted += 1
print(f"Converted={converted}, already_present={skipped}, failed_or_unsupported={failed}")
PY

echo "[3/4] Solve missing games with Strict + HypIG settings"
python3 - <<'PY'
import json
import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/user")
from method.avalon_logs_solver import QUICK_SETTINGS, solve_one

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)
timeout_log = out_dir / "timeouts.txt"
per_game_timeout = int(os.environ.get("PER_GAME_TIMEOUT_SECONDS", "90"))
job_time_budget = int(os.environ.get("JOB_TIME_BUDGET_SECONDS", "3000"))

all_files = sorted(in_dir.glob("*_constraints.json"))
timed_out_before = set()
if timeout_log.exists():
    timed_out_before = {
        line.strip()
        for line in timeout_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
missing = [
    fp for fp in all_files
    if not (out_dir / f"{fp.stem}_solve.json").exists()
    and fp.name not in timed_out_before
]

def player_count(fp: Path) -> int:
    try:
        with fp.open(encoding="utf-8") as f:
            return len(json.load(f).get("players", []))
    except Exception:
        return 99

missing.sort(key=lambda fp: (player_count(fp), fp.name))
print(f"Constraint files={len(all_files)}, missing_solve_outputs={len(missing)}")
if timed_out_before:
    print(f"Skipping {len(timed_out_before)} files that timed out in earlier attempts.")
print(f"Per-game timeout={per_game_timeout}s, job solve budget={job_time_budget}s")

class SolveTimeout(Exception):
    pass

def timeout_handler(signum, frame):
    raise SolveTimeout()

signal.signal(signal.SIGALRM, timeout_handler)

start = time.time()
solved = errors = timed_out = skipped_for_budget = 0
for fp in missing:
    elapsed = time.time() - start
    if elapsed >= job_time_budget:
        skipped_for_budget = len(missing) - solved - errors - timed_out
        print(
            f"  stopping solve loop after {elapsed / 60:.1f}m "
            f"to leave time for evaluation; remaining_this_pass={skipped_for_budget}",
            flush=True,
        )
        break
    dst = out_dir / f"{fp.stem}_solve.json"
    try:
        signal.alarm(per_game_timeout)
        result = solve_one(fp, settings=QUICK_SETTINGS)
        signal.alarm(0)
        dst.write_text(json.dumps(result), encoding="utf-8")
        solved += 1
        if solved % 10 == 0:
            elapsed = max(time.time() - start, 1e-9)
            rate = solved / elapsed
            remaining = len(missing) - solved
            eta_min = remaining / rate / 60 if rate else 0
            print(
                f"  solved {solved}/{len(missing)} "
                f"({rate:.3f}/s, ETA {eta_min:.1f}m)",
                flush=True,
            )
    except SolveTimeout:
        signal.alarm(0)
        timed_out += 1
        with timeout_log.open("a", encoding="utf-8") as f:
            f.write(fp.name + "\n")
        print(f"  TIMEOUT {fp.name} after {per_game_timeout}s; skipping future attempts", flush=True)
    except Exception as exc:
        signal.alarm(0)
        errors += 1
        print(f"  ERROR {fp.name}: {exc}", flush=True)

elapsed_min = (time.time() - start) / 60
print(
    f"Solved_new={solved}, timeouts={timed_out}, errors={errors}, "
    f"budget_skipped={skipped_for_budget}, elapsed={elapsed_min:.1f}m"
)
PY

echo "[4/4] Evaluate and validate"
bash scripts/evaluate.sh avalonlogs data/avalonlogs_solve scoring/scores.json
python3 validate.py --compare

echo "Complete: $(date)"
