#!/usr/bin/env python3
"""
Hidden test evaluator for AvalonLogs hidden-role inference.

The held-out games live only in eval/test/heldout.dat (encoded).  The
evaluator:

  1. decodes the held-out *inputs* (game prefixes + viewpoint information,
     no roles) and writes them to a fresh temporary directory;
  2. runs the method on disk through the fixed interface
         bash scripts/predict.sh <input_dir> <output_dir>
     while the held-out file is made unreadable;
  3. only after the method returns, decodes the held-out roles in memory and
     recomputes every score from the raw predictions;
  4. writes scoring/scores_test.json with one entry per method name found in
     the predictions.

A method is scored only if it returns a valid prediction for every instance
(normalised per-player distributions over the declared roles whose role
totals match the declared composition, plus a complete assignment with the
declared role counts) and the predictor exits with status 0.  Otherwise the
method gets the worst value of every metric in every experiment.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
HELDOUT = Path(__file__).resolve().parent / "heldout.dat"
HELDOUT_SHA256 = "ae8e3a1bf8e98f09ccbc9fcbaf3e46b90f00000bd79cbd0fb75bd30059508975"
SECRET = b"avalonlogs-heldout-v2/4b1f0c9e7d"
SLICE = "test"
VIEW_KEY = {"objective": "Obj", "merlin": "MRL", "percival": "PCV", "morgana": "MRG",
            "loyal_follower": "LSV", "evil_minion": "EVM"}
VIEWS = ["Obj", "MRL", "PCV", "MRG", "LSV", "EVM"]
SIZES = [5, 6, 7, 8, 9, 10]
WORST = {"brier": 2.0, "marginal": 0.0}
ROW_TOL = 1e-3
COL_TOL = 1e-2


def exp_name(n: int) -> str:
    return f"avalonlogs_{n}player"


# ------------------------------------------------------------ held-out data
def _keystream(section: str, n: int) -> bytes:
    key = hashlib.sha256(SECRET + section.encode()).digest()
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def decode_section(blob: Dict[str, str], section: str):
    raw = base64.b64decode(blob[section])
    ks = _keystream(section, len(raw))
    plain = (int.from_bytes(raw, "big") ^ int.from_bytes(ks, "big")).to_bytes(len(raw), "big")
    return json.loads(zlib.decompress(plain).decode("utf-8"))


def read_heldout() -> Dict[str, str]:
    data = HELDOUT.read_bytes()
    if HELDOUT_SHA256 != "__HELDOUT_SHA256__" and hashlib.sha256(data).hexdigest() != HELDOUT_SHA256:
        raise SystemExit("eval/test/heldout.dat does not match its recorded checksum")
    blob = {}
    for line in data.decode("ascii").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            blob[k.strip()] = v.strip()
    return blob


# ------------------------------------------------------------- validation
def valid_prediction(pred, inst) -> bool:
    players = inst["players"]
    counts = {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}
    if not isinstance(pred, dict):
        return False
    post, best = pred.get("posterior"), pred.get("best")
    if not isinstance(post, dict) or set(post) != set(players):
        return False
    col = Counter()
    for p in players:
        row = post[p]
        if not isinstance(row, dict):
            return False
        s = 0.0
        for r, v in row.items():
            if r not in counts or isinstance(v, bool) or not isinstance(v, (int, float)):
                return False
            if not math.isfinite(v) or v < -1e-9 or v > 1.0 + 1e-6:
                return False
            s += v
            col[r] += v
        if abs(s - 1.0) > ROW_TOL:
            return False
    if any(abs(col[r] - c) > COL_TOL for r, c in counts.items()):
        return False
    if not isinstance(best, dict) or set(best) != set(players):
        return False
    if any(not isinstance(r, str) for r in best.values()):
        return False
    return Counter(best.values()) == Counter(counts)


def instance_metrics(pred, inst, truth) -> Dict[str, float]:
    roles = [r for r, c in inst["role_counts"].items() if int(c) > 0]
    brier = marginal = 0.0
    for p in inst["players"]:
        row = pred["posterior"][p]
        t = truth[p]
        q = {r: min(max(float(row.get(r, 0.0)), 0.0), 1.0) for r in roles}
        marginal += q[t]
        brier += sum((q[r] - (1.0 if r == t else 0.0)) ** 2 for r in roles)
    n = len(inst["players"])
    return {"brier": brier / n, "marginal": marginal / n}


def sanitize(name) -> Optional[str]:
    if not isinstance(name, str):
        return None
    clean = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name.strip().lstrip("+")).strip("_")
    if not clean or clean.startswith("_"):
        return None
    return clean


def fallback_method_names() -> List[str]:
    """Names used to record a run that produced no predictions at all."""
    names = set()
    try:
        ref = json.loads((REPO / "scoring" / "reference.json").read_text())
        for n in SIZES:
            names |= set(ref["experiments"][exp_name(n)]["results"])
    except Exception:
        pass
    return sorted(names) or ["FAILED_RUN"]


# ---------------------------------------------------------------- runner
def run_predictor(cmd: str, instances: List[dict], workdir: Path) -> tuple:
    in_dir, out_dir = workdir / "input", workdir / "output"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "instances.json").write_text(json.dumps(
        {"format": "avalonlogs-instances-v2", "instances": instances}))
    old_mode = None
    try:
        old_mode = stat.S_IMODE(HELDOUT.stat().st_mode)
        os.chmod(HELDOUT, 0)
    except OSError:
        old_mode = None
    try:
        proc = subprocess.run(shlex.split(cmd) + [str(in_dir), str(out_dir)], cwd=str(REPO))
        rc = proc.returncode
    except OSError as exc:
        print(f"predictor could not start: {exc}", file=sys.stderr)
        rc = 127
    finally:
        if old_mode is not None:
            os.chmod(HELDOUT, old_mode)
    preds = {}
    try:
        data = json.loads((out_dir / "predictions.json").read_text())
        preds = data.get("predictions", {}) if isinstance(data, dict) else {}
        if not isinstance(preds, dict):
            preds = {}
    except Exception as exc:
        print(f"could not read predictions: {exc}", file=sys.stderr)
    return rc, preds


def score(instances, labels, preds, rc):
    by_cell: Dict[tuple, List[dict]] = defaultdict(list)
    for inst in instances:
        by_cell[(inst["n_players"], VIEW_KEY[inst["view"]["perspective"]])].append(inst)

    names = set()
    for v in preds.values():
        if isinstance(v, dict):
            names |= {s for s in (sanitize(k) for k in v) if s}
    raw_name = {}
    for v in preds.values():
        if isinstance(v, dict):
            for k in v:
                s = sanitize(k)
                if s and s not in raw_name:
                    raw_name[s] = k

    results: Dict[str, Dict[str, Dict[str, float]]] = {exp_name(n): {} for n in SIZES}
    status, per_instance = {}, {}
    for name in sorted(names):
        cells = defaultdict(list)
        ok = rc == 0
        reason = "" if ok else f"predictor exit status {rc}"
        if ok:
            for inst in instances:
                entry = preds.get(inst["instance_id"])
                pred = None
                if isinstance(entry, dict):
                    pred = next((p for k, p in entry.items() if sanitize(k) == name), None)
                if pred is None or not valid_prediction(pred, inst):
                    ok = False
                    reason = f"missing or invalid prediction for {inst['instance_id']}"
                    break
                m = instance_metrics(pred, inst, labels[inst["instance_id"]])
                cells[(inst["n_players"], VIEW_KEY[inst["view"]["perspective"]])].append(m)
                per_instance.setdefault(name, {})[inst["instance_id"]] = m
        status[name] = "ok" if ok else f"failed: {reason}"
        for n in SIZES:
            vals = {}
            for view in VIEWS:
                for metric in ("brier", "marginal"):
                    if ok and cells.get((n, view)):
                        xs = [c[metric] for c in cells[(n, view)]]
                        vals[f"{view}_{metric}"] = round(sum(xs) / len(xs), 6)
                    else:
                        vals[f"{view}_{metric}"] = WORST[metric]
            results[exp_name(n)][name] = vals
    if not names:
        for name in fallback_method_names():
            status[name] = "failed: no predictions"
            for n in SIZES:
                results[exp_name(n)][name] = {f"{v}_{m}": WORST[m] for v in VIEWS for m in ("brier", "marginal")}
    counts = {exp_name(n): {v: len(by_cell.get((n, v), [])) for v in VIEWS} for n in SIZES}
    return results, status, counts, per_instance


def main() -> None:
    ap = argparse.ArgumentParser(description="Score the method on the hidden AvalonLogs test instances.")
    ap.add_argument("--output", type=Path, default=REPO / "scoring" / "scores_test.json")
    ap.add_argument("--predict-cmd", default=os.environ.get("PREDICT_CMD", "bash scripts/predict.sh"),
                    help="Predictor command; receives <input_dir> <output_dir>.")
    ap.add_argument("--per-instance", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    blob = read_heldout()
    instances = decode_section(blob, "inputs")["instances"]
    work = Path(tempfile.mkdtemp(prefix="avalon_test_"))
    try:
        rc, preds = run_predictor(args.predict_cmd, instances, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    labels = decode_section(blob, "labels")
    results, status, counts, per_instance = score(instances, labels, preds, rc)

    out = {"experiments": {}, "metadata": {
        "slice": SLICE,
        "n_instances": len(instances),
        "n_instances_by_experiment_view": counts,
        "predictor_exit_status": rc,
        "method_status": status,
        "protocol": "one held-out game prefix per instance, one viewpoint per game; "
                    "Brier score (ranked) and marginal accuracy (reported) per viewpoint",
    }}
    for n in SIZES:
        out["experiments"][exp_name(n)] = {
            "description": f"AvalonLogs {n}-player held-out test instances",
            "results": results[exp_name(n)],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))
    if args.per_instance is not None:
        args.per_instance.parent.mkdir(parents=True, exist_ok=True)
        args.per_instance.write_text(json.dumps(per_instance))
    print(f"Test scores written to {args.output}")
    for name, st in sorted(status.items()):
        print(f"  {name}: {st}")


if __name__ == "__main__":
    main()
