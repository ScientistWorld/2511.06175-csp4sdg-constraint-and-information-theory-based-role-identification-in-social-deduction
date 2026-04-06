"""
Compute marginal accuracy and MAP accuracy from CSP solver results.

For AvalonLogs, computes per-game, then aggregates across games.
For Avalon-NLU and Mafia, computes per-game per-quest, then aggregates.

Output: scores.json with per-experiment per-method metrics.
"""

import json
import sys
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_json_files(dir_path: Path, pattern: str = "*.json"):
    """Load all JSON files in a directory."""
    for fp in sorted(dir_path.glob(pattern)):
        with open(fp, encoding="utf-8") as f:
            yield fp.stem, json.load(f)


# ------------------------------------------------------------------
# AvalonLogs evaluator
# ------------------------------------------------------------------

def compute_avalonlogs_game_metrics(game: Dict) -> Dict:
    """
    For a single AvalonLogs game, compute per-view per-setting metrics.
    Views: objective, merlin, percival, morgana, servant, evil_minion
    Settings: Strict, +Assert, +HypIG, +HypM, +TurnIG
    """
    truth = game["players"]
    P = len(truth)
    out = {}

    # Map role views to canonical names
    ROLE_MAP = {
        "merlin": "MRL", "percival": "PCV", "morgana": "MRG",
        "servant": "LSV", "loyal_follower": "LSV", "loyal_servant": "LSV",
        "assassin": "ASN", "evil_minion": "EVM", "evil-minion": "EVM",
        "mordred": "EVM", "oberon": "EVM",
    }

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            # Map view name to canonical
            canonical_view = ROLE_MAP.get(view.lower(), view)

            for setting, data in settings.items():
                post = data.get("posterior", {})
                best = data.get("best", {})

                if not post:
                    continue

                # marginal accuracy
                marg = sum(
                    post.get(p, {}).get(r, 0.0)
                    for p, r in truth.items()
                ) / P

                # map accuracy
                correct = sum(
                    1 for p, r in truth.items()
                    if best.get(p) == r
                )
                map_acc = correct / P

                key = (canonical_view, setting)
                rec = out.setdefault(key, {"marg_sum": 0.0, "map_sum": 0.0, "count": 0})
                rec["marg_sum"] += marg
                rec["map_sum"] += map_acc
                rec["count"] += 1

    # average within game
    for rec in out.values():
        rec["marg_mean"] = rec["marg_sum"] / rec["count"]
        rec["map_mean"] = rec["map_sum"] / rec["count"]

    return out


def aggregate_avalonlogs(metrics_per_game: List[Dict]) -> Dict:
    """Aggregate per-game metrics into final averages."""
    agg = defaultdict(lambda: {"marg_sum": 0.0, "map_sum": 0.0, "count": 0})
    for gm in metrics_per_game:
        for k, rec in gm.items():
            agg[k]["marg_sum"] += rec["marg_mean"]
            agg[k]["map_sum"] += rec["map_mean"]
            agg[k]["count"] += 1

    final = {}
    for (view, setting), rec in agg.items():
        if rec["count"] == 0:
            continue
        final[f"{view}_{setting}"] = {
            "view": view,
            "setting": setting,
            "marginal_accuracy": rec["marg_sum"] / rec["count"],
            "map_accuracy": rec["map_sum"] / rec["count"],
            "n_games": rec["count"],
        }
    return final


# ------------------------------------------------------------------
# Avalon-NLU evaluator (JSONL format)
# ------------------------------------------------------------------

def compute_avalonnlu_game_metrics(game: Dict) -> Dict:
    """For a single Avalon-NLU game, compute per-view per-setting metrics."""
    truth = game["players"]
    P = len(truth)
    out = {}

    ROLE_MAP = {
        "merlin": "MRL", "percival": "PCV", "morgana": "MRG",
        "servant": "LSV", "loyal_follower": "LSV", "assassin": "ASN",
        "objective": "Obj",
    }

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            canonical_view = ROLE_MAP.get(view.lower(), view)

            for setting, data in settings.items():
                post = data.get("posterior", {})
                best = data.get("best", {})

                if not post:
                    continue

                marg = sum(
                    post.get(p, {}).get(r, 0.0)
                    for p, r in truth.items()
                ) / P

                correct = sum(1 for p, r in truth.items() if best.get(p) == r)
                map_acc = correct / P

                key = (canonical_view, setting)
                rec = out.setdefault(key, {"marg_sum": 0.0, "map_sum": 0.0, "count": 0})
                rec["marg_sum"] += marg
                rec["map_sum"] += map_acc
                rec["count"] += 1

    for rec in out.values():
        rec["marg_mean"] = rec["marg_sum"] / rec["count"]
        rec["map_mean"] = rec["map_sum"] / rec["count"]

    return out


def aggregate_avalonnlu(metrics_per_game: List[Dict]) -> Dict:
    """Aggregate Avalon-NLU results."""
    agg = defaultdict(lambda: {"marg_sum": 0.0, "map_sum": 0.0, "count": 0})
    for gm in metrics_per_game:
        for k, rec in gm.items():
            agg[k]["marg_sum"] += rec["marg_mean"]
            agg[k]["map_sum"] += rec["map_mean"]
            agg[k]["count"] += 1

    final = {}
    for (view, setting), rec in agg.items():
        if rec["count"] == 0:
            continue
        final[f"{view}_{setting}"] = {
            "view": view,
            "setting": setting,
            "marginal_accuracy": rec["marg_sum"] / rec["count"],
            "map_accuracy": rec["map_sum"] / rec["count"],
            "n_games": rec["count"],
        }
    return final


# ------------------------------------------------------------------
# Main evaluation driver
# ------------------------------------------------------------------

def evaluate(
    results_dir: Path,
    output_path: Path,
    dataset: str = "avalonlogs",
    condition: str = "Truth",
) -> Dict:
    """
    Evaluate CSP results and write scores.json.

    Args:
        results_dir: Directory containing solver results
        output_path: Path to write scores.json
        dataset: "avalonlogs", "avalonnlu", or "mafia"
        condition: "Truth" or "Lie" (for Avalon-NLU/Mafia)

    Returns:
        The computed scores dictionary
    """
    scores = {"experiments": {}, "metadata": {"dataset": dataset, "condition": condition}}

    if dataset == "avalonlogs":
        game_metrics = []
        for fp in sorted(results_dir.glob("*_solve.json")):
            with open(fp, encoding="utf-8") as f:
                game = json.load(f)
            gm = compute_avalonlogs_game_metrics(game)
            game_metrics.append(gm)

        agg = aggregate_avalonlogs(game_metrics)

        # Build scores structure
        # Experiment: avalonlogs_main — 6-player and 9-player results
        # Also group by view
        for key, vals in agg.items():
            view = vals["view"]
            setting = vals["setting"]
            method_name = f"CSP_{setting}"

            exp_name = f"avalonlogs_{setting.lower().replace('+', 'plus')}"
            if exp_name not in scores["experiments"]:
                scores["experiments"][exp_name] = {
                    "description": f"AvalonLogs CSP {setting} results",
                    "results": {},
                }
            scores["experiments"][exp_name]["results"][method_name] = {
                "marginal_accuracy": round(vals["marginal_accuracy"], 4),
                "map_accuracy": round(vals["map_accuracy"], 4),
                "n_games": vals["n_games"],
            }

    elif dataset == "avalonnlu":
        game_metrics = []
        for fp in sorted(results_dir.glob("*.jsonl")):
            for game in load_jsonl(fp):
                if game.get("cond") != condition:
                    continue
                gm = compute_avalonnlu_game_metrics(game)
                game_metrics.append(gm)

        agg = aggregate_avalonnlu(game_metrics)
        for key, vals in agg.items():
            view = vals["view"]
            setting = vals["setting"]
            method_name = f"CSP_{setting}"

            exp_name = f"avalonnlu_{setting.lower().replace('+', 'plus')}"
            if exp_name not in scores["experiments"]:
                scores["experiments"][exp_name] = {
                    "description": f"Avalon-NLU CSP {setting} ({condition})",
                    "results": {},
                }
            scores["experiments"][exp_name]["results"][method_name] = {
                f"{view.lower()}_marginal": round(vals["marginal_accuracy"], 4),
                f"{view.lower()}_map": round(vals["map_accuracy"], 4),
                "n_games": vals["n_games"],
            }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    print(f"Scores written to {output_path}")
    return scores


# ------------------------------------------------------------------
# Entry point for eval/evaluate.py
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate CSP results")
    parser.add_argument("--results-dir", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--dataset", type=str, default="avalonlogs",
                        choices=["avalonlogs", "avalonnlu", "mafia"])
    parser.add_argument("--condition", type=str, default="Truth",
                        choices=["Truth", "Lie"])
    args = parser.parse_args()

    evaluate(
        results_dir=Path(args.results_dir),
        output_path=Path(args.output),
        dataset=args.dataset,
        condition=args.condition,
    )
