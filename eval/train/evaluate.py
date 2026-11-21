#!/usr/bin/env python3
"""
Train-slice evaluator for AvalonLogs hidden-role inference.

Builds evaluation instances from the visible games in data/avalonlogs_raw
(the held-out test games are not there), runs the method through the fixed
interface

    bash scripts/predict.sh <input_dir> <output_dir>

and scores the predictions exactly like the hidden test evaluator: one game
prefix per instance (uniformly sampled completed mission), one viewpoint per
game (balanced within each player count), Brier score (ranked) and marginal
accuracy (reported) per viewpoint and player count.  Invalid or missing
predictions, or a non-zero predictor exit status, fail the method: it gets the
worst value of every metric in every experiment.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
RAW_DIR = REPO / "data" / "avalonlogs_raw"
SEED = "avalonlogs-train-v2"
SLICE = "train"
GOOD = {"loyal_follower", "merlin", "percival", "servant"}
VIEW_ORDER = ["objective", "merlin", "percival", "morgana", "loyal_follower", "evil_minion"]
VIEW_KEY = {"objective": "Obj", "merlin": "MRL", "percival": "PCV", "morgana": "MRG",
            "loyal_follower": "LSV", "evil_minion": "EVM"}
VIEWS = ["Obj", "MRL", "PCV", "MRG", "LSV", "EVM"]
SIZES = [5, 6, 7, 8, 9, 10]
WORST = {"brier": 2.0, "marginal": 0.0}
ROW_TOL = 1e-3
COL_TOL = 1e-2


def exp_name(n: int) -> str:
    return f"avalonlogs_{n}player"


# ------------------------------------------------------- instance building
def canon(role):
    return role.strip().lower().replace(" ", "_")


def load_game(path):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict) or not {"players", "missions", "outcome"} <= set(raw):
        return None
    names = [p["name"] for p in raw["players"]]
    roles = {r["name"]: canon(r["role"]) for r in raw["outcome"].get("roles", [])}
    if len(set(names)) != len(names) or set(roles) != set(names) or not 5 <= len(names) <= 10:
        return None
    done = []
    for m in raw.get("missions", []):
        if m.get("state") not in ("SUCCESS", "FAIL"):
            break
        done.append(m)
    if not done:
        return None
    ok = set(names)
    for m in done:
        if not set(m.get("team", [])) <= ok or "numFails" not in m:
            return None
        for pr in m.get("proposals", []):
            if pr.get("proposer") not in ok or not set(pr.get("team", [])) <= ok \
                    or not set(pr.get("votes", [])) <= ok:
                return None
    return {"names": names, "roles": roles, "missions": done}


def build_instance(game, q, view, rng, instance_id):
    names = game["names"]
    alias = {n: f"P{i + 1}" for i, n in enumerate(names)}
    counts = Counter(game["roles"].values())
    missions = []
    for idx, m in enumerate(game["missions"][:q], 1):
        props = []
        for pr in m.get("proposals", []):
            appr = set(pr.get("votes", []))
            props.append({
                "proposer": alias[pr["proposer"]],
                "team": [alias[p] for p in pr["team"]],
                "approve": [alias[p] for p in names if p in appr],
                "reject": [alias[p] for p in names if p not in appr],
                "approved": pr.get("state") == "APPROVED",
            })
        missions.append({"mission": idx, "team_size": m["teamSize"], "fails_required": m["failsRequired"],
                         "proposals": props, "team": [alias[p] for p in m["team"]],
                         "num_fails": m["numFails"], "result": m["state"]})
    seat = {alias[n]: i for i, n in enumerate(names)}
    lab = {alias[n]: r for n, r in game["roles"].items()}
    spec = {"perspective": view}
    if view != "objective":
        viewers = sorted([p for p, r in lab.items() if r == view], key=seat.get)
        viewer = viewers[rng.randrange(len(viewers))]
        spec.update({"viewer": viewer, "viewer_role": view})
        if view == "merlin":
            spec["sees_evil"] = sorted([p for p, r in lab.items() if r not in GOOD and r != "mordred"], key=seat.get)
        elif view == "percival":
            spec["merlin_candidates"] = sorted([p for p, r in lab.items() if r in ("merlin", "morgana")], key=seat.get)
        elif view in ("morgana", "evil_minion"):
            spec["sees_evil"] = sorted([p for p, r in lab.items()
                                        if r not in GOOD and r != "oberon" and p != viewer], key=seat.get)
    inst = {"instance_id": instance_id, "n_players": len(names),
            "players": [alias[n] for n in names],
            "role_counts": dict(sorted(counts.items())),
            "good_roles": sorted(r for r in counts if r in GOOD),
            "evil_roles": sorted(r for r in counts if r not in GOOD),
            "missions": missions, "view": spec}
    return inst, lab


def build_train_instances(raw_dir: Path, limit: Optional[int] = None):
    games = []
    for fp in sorted(raw_dir.iterdir()):
        if fp.is_file():
            g = load_game(fp)
            if g is not None:
                games.append((fp.name, g))
    rng = random.Random(SEED)
    by_size = {}
    for label, g in games:
        by_size.setdefault(len(g["names"]), []).append((label, g))
    insts, labels = [], {}
    for n in sorted(by_size):
        items = by_size[n]
        rng.shuffle(items)
        if limit:
            items = items[:limit]
        vc = Counter()
        for _label, g in items:
            present = set(g["roles"].values())
            av = [v for v in VIEW_ORDER if v == "objective" or v in present]
            low = min(vc[v] for v in av)
            view = rng.choice([v for v in av if vc[v] == low])
            vc[view] += 1
            q = rng.randint(1, len(g["missions"]))
            iid = f"r{rng.getrandbits(48):012x}"
            inst, lab = build_instance(g, q, view, rng, iid)
            insts.append(inst)
            labels[iid] = lab
    rng.shuffle(insts)
    return insts, labels


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
    names = set()
    try:
        ref = json.loads((REPO / "scoring" / "reference.json").read_text())
        for n in SIZES:
            names |= set(ref["experiments"][exp_name(n)]["results"])
    except Exception:
        pass
    return sorted(names) or ["FAILED_RUN"]


def run_predictor(cmd: str, instances: List[dict], workdir: Path):
    in_dir, out_dir = workdir / "input", workdir / "output"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "instances.json").write_text(json.dumps(
        {"format": "avalonlogs-instances-v2", "instances": instances}))
    try:
        rc = subprocess.run(shlex.split(cmd) + [str(in_dir), str(out_dir)], cwd=str(REPO)).returncode
    except OSError as exc:
        print(f"predictor could not start: {exc}", file=sys.stderr)
        rc = 127
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
    by_cell = defaultdict(list)
    for inst in instances:
        by_cell[(inst["n_players"], VIEW_KEY[inst["view"]["perspective"]])].append(inst)
    names = set()
    for v in preds.values():
        if isinstance(v, dict):
            names |= {s for s in (sanitize(k) for k in v) if s}
    results = {exp_name(n): {} for n in SIZES}
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
    ap = argparse.ArgumentParser(description="Score the method on train instances built from visible games.")
    ap.add_argument("--output", type=Path, default=REPO / "scoring" / "scores_train.json")
    ap.add_argument("--predict-cmd", default=os.environ.get("PREDICT_CMD", "bash scripts/predict.sh"),
                    help="Predictor command; receives <input_dir> <output_dir>.")
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--limit-per-size", type=int, default=None,
                    help="Use at most this many games per player count (quick development runs).")
    ap.add_argument("--per-instance", type=Path, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--dump-instances", type=Path, default=None,
                    help="Also write the train instances and their roles to this JSON file.")
    args = ap.parse_args()

    instances, labels = build_train_instances(args.raw_dir, args.limit_per_size)
    if args.dump_instances is not None:
        args.dump_instances.write_text(json.dumps({"instances": instances, "labels": labels}))
    work = Path(tempfile.mkdtemp(prefix="avalon_train_"))
    try:
        rc, preds = run_predictor(args.predict_cmd, instances, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    results, status, counts, per_instance = score(instances, labels, preds, rc)
    out = {"experiments": {}, "metadata": {
        "slice": SLICE,
        "n_instances": len(instances),
        "n_instances_by_experiment_view": counts,
        "predictor_exit_status": rc,
        "method_status": status,
        "protocol": "one visible game prefix per instance, one viewpoint per game; "
                    "Brier score (ranked) and marginal accuracy (reported) per viewpoint",
    }}
    for n in SIZES:
        out["experiments"][exp_name(n)] = {
            "description": f"AvalonLogs {n}-player train instances (visible games)",
            "results": results[exp_name(n)],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2))
    if args.per_instance is not None:
        args.per_instance.parent.mkdir(parents=True, exist_ok=True)
        args.per_instance.write_text(json.dumps(per_instance))
    print(f"Train scores written to {args.output}")
    for name, st in sorted(status.items()):
        print(f"  {name}: {st}")


if __name__ == "__main__":
    main()
