"""
Compute marginal accuracy and MAP accuracy from CSP solver results.

For AvalonLogs, computes per-game, then aggregates across games.
For Avalon-NLU and Mafia, computes per-game per-quest, then aggregates.

Output: scores.json with per-experiment per-method metrics.
"""

import json
import re
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

    # Map role views to canonical names.
    # Handle both base names (merlin, loyal_follower) and numbered views
    # (merlin1, loyal_follower1, evil_minion1, etc.) from the solver.
    def canonicalize(view: str) -> str:
        v = view.lower()
        # Strip trailing numbers (e.g. "loyal_follower1" -> "loyal_follower")
        import re
        v_stripped = re.sub(r'\d+$', '', v)
        if v_stripped in ("merlin",): return "MRL"
        if v_stripped in ("percival",): return "PCV"
        if v_stripped in ("morgana",): return "MRG"
        if v_stripped in ("servant", "loyal_follower", "loyal_servant"): return "LSV"
        if v_stripped in ("assassin",): return "ASN"
        if v_stripped in ("evil_minion", "evil-minion", "mordred", "oberon"): return "EVM"
        if v_stripped in ("objective",): return "Obj"
        return v_stripped  # fallback

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            # Map view name to canonical
            canonical_view = canonicalize(view)

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

    def canonicalize(view: str) -> str:
        v = view.lower()
        # Strip trailing numbers (e.g. "merlin1" -> "merlin")
        v_stripped = re.sub(r'\d+$', '', v)
        if v_stripped in ("merlin",): return "MRL"
        if v_stripped in ("percival",): return "PCV"
        if v_stripped in ("morgana",): return "MRG"
        if v_stripped in ("servant", "loyal_follower", "loyal_servant"): return "LSV"
        if v_stripped in ("assassin",): return "ASN"
        if v_stripped in ("evil_minion", "evil-minion", "mordred", "oberon"): return "EVM"
        if v_stripped in ("objective",): return "Obj"
        return v_stripped  # fallback

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            canonical_view = canonicalize(view)

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
        # Load reference.json to know which methods to include
        ref_path = output_path.parent / "reference.json"
        ref_experiments = {}
        if ref_path.exists():
            try:
                with open(ref_path, encoding="utf-8") as f:
                    ref_data = json.load(f)
                ref_experiments = ref_data.get("experiments", {})
            except Exception:
                pass

        # Collect game-level metrics, keyed by (player_count, setting, view).
        # The paper averages over quests within each game first, then averages
        # across games. Keeping game means here prevents longer games from
        # receiving extra weight.
        by_size: Dict[int, Dict[str, Dict[str, List]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )

        game_counts = {}  # player_count -> n_games

        for fp in sorted(results_dir.glob("*_solve.json")):
            try:
                with open(fp, encoding="utf-8") as f:
                    game = json.load(f)
            except Exception:
                continue

            truth = game.get("players", {})
            n_players = len(truth)
            game_counts[n_players] = game_counts.get(n_players, 0) + 1

            for (view, setting), rec in compute_avalonlogs_game_metrics(game).items():
                by_size[n_players][setting][view].append((rec["marg_mean"], rec["map_mean"]))

        # Map player size to experiment name (matching reference.json)
        SIZE_TO_EXP = {
            5: "avalonlogs_5player",
            6: "avalonlogs_6player",
            7: "avalonlogs_7player",
            8: "avalonlogs_8player",
            9: "avalonlogs_9player",
            10: "avalonlogs_10player",
        }

        for size, settings_data in sorted(by_size.items()):
            exp_name = SIZE_TO_EXP.get(size)
            if exp_name is None:
                continue  # Skip 7-8 player games

            scores["experiments"][exp_name] = {"description": f"AvalonLogs {size}-player CSP results", "results": {}}

            for setting, views_data in settings_data.items():
                # Map setting name to method name matching reference.json
                # reference.json uses "CSP_Strict", "CSP_HypIG", etc.
                setting_clean = setting.replace("+", "")
                mname = f"CSP_{setting_clean}"

                # Only include methods that exist in reference.json for this experiment
                ref_exp = ref_experiments.get(exp_name, {})
                ref_methods = set(ref_exp.get("results", {}).keys())
                if ref_methods and mname not in ref_methods:
                    continue

                scores["experiments"][exp_name]["results"][mname] = {}

                # Include views matching reference.json metrics (marginal only for AvalonLogs)
                VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM", "Obj"}
                for view, vals in views_data.items():
                    if view not in VALID_VIEWS:
                        continue
                    if not vals:
                        continue
                    margs = [v[0] for v in vals]
                    avg_marg = round(sum(margs) / len(margs), 4)
                    scores["experiments"][exp_name]["results"][mname][f"{view}_marginal"] = avg_marg

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
    print(f"Experiments: {list(scores['experiments'].keys())}")
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
