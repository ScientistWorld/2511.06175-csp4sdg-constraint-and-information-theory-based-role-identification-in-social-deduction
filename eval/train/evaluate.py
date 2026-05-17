#!/usr/bin/env python3
"""
Train-slice evaluator for pre-generated Avalon solver outputs.

This file is intentionally self-contained within eval/train. It reads method
artifacts already present on disk, selects a deterministic stratified half of
the evaluation pool, and writes scores_train.json-compatible output.
"""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


SPLIT_NAME = "train"
SPLIT_SEED = "avalon-scientist-gym-v1"
VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM", "Obj", "BYS", "MAF"}
SIZE_TO_EXP = {
    5: "avalonlogs_5player",
    6: "avalonlogs_6player",
    7: "avalonlogs_7player",
    8: "avalonlogs_8player",
    9: "avalonlogs_9player",
    10: "avalonlogs_10player",
}


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def stable_key(label: str) -> str:
    return hashlib.sha256(f"{SPLIT_SEED}:{label}".encode("utf-8")).hexdigest()


def canonicalize_view(view: str) -> str:
    v = re.sub(r"\d+$", "", view.lower())
    if v == "merlin":
        return "MRL"
    if v == "percival":
        return "PCV"
    if v == "morgana":
        return "MRG"
    if v in {"servant", "loyal_follower", "loyal_servant"}:
        return "LSV"
    if v == "assassin":
        return "ASN"
    if v in {"evil_minion", "evil-minion", "mordred", "oberon"}:
        return "EVM"
    if v == "objective":
        return "Obj"
    if v in {"bys", "bystander"}:
        return "BYS"
    if v in {"maf", "mafia", "mafioso"}:
        return "MAF"
    return v


def method_name_for_setting(setting: str) -> str:
    clean = setting.strip().lstrip("+")
    clean = re.sub(r"[^A-Za-z0-9]+", "_", clean).strip("_")
    if not clean:
        clean = "Unnamed"
    if clean.startswith(("CSP_", "LLM_", "Random")):
        return clean
    return f"CSP_{clean}"


def select_half_by_group(items: List[Tuple[str, Any]], slice_name: str) -> List[Any]:
    ordered = sorted(items, key=lambda item: stable_key(item[0]))
    midpoint = (len(ordered) + 1) // 2
    selected = ordered[:midpoint] if slice_name == "train" else ordered[midpoint:]
    return [item for _, item in selected]


def compute_game_metrics(game: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, float]]:
    truth = game.get("players", {})
    player_count = len(truth)
    out: Dict[Tuple[str, str], Dict[str, float]] = {}
    if player_count == 0:
        return out

    rounds = game.get("quests") or game.get("days") or {}
    for round_obj in rounds.values():
        for view, settings in round_obj.items():
            canonical_view = canonicalize_view(view)
            for setting, data in settings.items():
                posterior = data.get("posterior", {})
                best = data.get("best", {})
                if not posterior:
                    continue

                marginal = sum(
                    posterior.get(player, {}).get(role, 0.0)
                    for player, role in truth.items()
                ) / player_count
                map_acc = sum(
                    1 for player, role in truth.items() if best.get(player) == role
                ) / player_count

                key = (canonical_view, method_name_for_setting(setting))
                rec = out.setdefault(key, {"marginal_sum": 0.0, "map_sum": 0.0, "count": 0.0})
                rec["marginal_sum"] += marginal
                rec["map_sum"] += map_acc
                rec["count"] += 1.0

    averaged = {}
    for key, rec in out.items():
        if rec["count"]:
            averaged[key] = {
                "marginal": rec["marginal_sum"] / rec["count"],
                "map": rec["map_sum"] / rec["count"],
            }
    return averaged


def empty_scores(dataset: str, condition: str) -> Dict[str, Any]:
    return {
        "experiments": {},
        "metadata": {
            "dataset": dataset,
            "condition": condition,
            "slice": SPLIT_NAME,
            "split_seed": SPLIT_SEED,
            "split_style": "deterministic stratified 50/50 split over pre-generated method output files",
        },
    }


def evaluate_avalonlogs(
    results_dir: Path,
    dataset: str,
    condition: str,
    method_filter: Optional[Dict[str, Set[str]]] = None,
) -> Dict[str, Any]:
    scores = empty_scores(dataset, condition)
    grouped_paths: Dict[int, List[Tuple[str, Path]]] = defaultdict(list)

    for path in sorted(results_dir.glob("*_solve.json")):
        game = load_json(path)
        if not game:
            continue
        player_count = len(game.get("players", {}))
        if player_count in SIZE_TO_EXP:
            grouped_paths[player_count].append((path.name, path))

    split_counts = {}
    by_exp_method_view: Dict[str, Dict[str, Dict[str, List[Dict[str, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for player_count, labelled_paths in grouped_paths.items():
        exp_name = SIZE_TO_EXP[player_count]
        selected_paths = select_half_by_group(labelled_paths, SPLIT_NAME)
        split_counts[exp_name] = len(selected_paths)

        for path in selected_paths:
            game = load_json(path)
            if not game:
                continue
            for (view, method_name), vals in compute_game_metrics(game).items():
                if view not in VALID_VIEWS:
                    continue
                if method_filter is not None and method_name not in method_filter.get(exp_name, set()):
                    continue
                by_exp_method_view[exp_name][method_name][view].append(vals)

    for exp_name in sorted(by_exp_method_view):
        scores["experiments"][exp_name] = {
            "description": f"AvalonLogs {exp_name.split('_')[1].replace('player', '-player')} {SPLIT_NAME} split results",
            "results": {},
        }
        exp_filter = method_filter.get(exp_name, set()) if method_filter is not None else None
        method_names = sorted(exp_filter) if exp_filter else sorted(by_exp_method_view[exp_name])
        for method_name in method_names:
            method_scores = {}
            for view, values in sorted(by_exp_method_view[exp_name].get(method_name, {}).items()):
                if values:
                    method_scores[f"{view}_marginal"] = round(sum(v["marginal"] for v in values) / len(values), 4)
            scores["experiments"][exp_name]["results"][method_name] = method_scores

    scores["metadata"]["n_selected_files_by_experiment"] = split_counts
    return scores


def evaluate_avalonnlu(
    results_dir: Path,
    dataset: str,
    condition: str,
    method_filter: Optional[Dict[str, Set[str]]] = None,
) -> Dict[str, Any]:
    scores = empty_scores(dataset, condition)
    labelled_games = []
    for path in sorted(results_dir.glob("*.jsonl")):
        for idx, game in enumerate(load_jsonl(path)):
            if game.get("cond") == condition:
                labelled_games.append((f"{path.name}:{idx}", game))

    selected_games = select_half_by_group(labelled_games, SPLIT_NAME)
    exp_name = f"avalonnlu_{condition.lower()}_main"
    by_method_view: Dict[str, Dict[str, Dict[str, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for game in selected_games:
        for (view, method_name), vals in compute_game_metrics(game).items():
            if method_filter is not None and method_name not in method_filter.get(exp_name, set()):
                continue
            by_method_view[method_name][view]["marginal"].append(vals["marginal"])
            by_method_view[method_name][view]["map"].append(vals["map"])

    if by_method_view or method_filter:
        scores["experiments"][exp_name] = {
            "description": f"Avalon-NLU {condition} {SPLIT_NAME} split results",
            "results": {},
        }
        exp_filter = method_filter.get(exp_name, set()) if method_filter is not None else None
        method_names = sorted(exp_filter) if exp_filter else sorted(by_method_view)
        for method_name in method_names:
            method_scores = {}
            for view, metrics in sorted(by_method_view.get(method_name, {}).items()):
                if metrics["marginal"]:
                    method_scores[f"{view}_marginal"] = round(sum(metrics["marginal"]) / len(metrics["marginal"]), 4)
                if metrics["map"]:
                    method_scores[f"{view}_map"] = round(sum(metrics["map"]) / len(metrics["map"]), 4)
            scores["experiments"][exp_name]["results"][method_name] = method_scores

    scores["metadata"]["n_selected_games"] = len(selected_games)
    return scores


def evaluate_mafia(
    results_dir: Path,
    dataset: str,
    condition: str,
    method_filter: Optional[Dict[str, Set[str]]] = None,
) -> Dict[str, Any]:
    scores = empty_scores(dataset, condition)
    labelled_games = []
    paths = [results_dir] if results_dir.is_file() else sorted(results_dir.glob("*.jsonl"))
    for path in paths:
        for idx, game in enumerate(load_jsonl(path)):
            if game.get("cond") == condition:
                labelled_games.append((f"{path.name}:{idx}", game))

    selected_games = select_half_by_group(labelled_games, SPLIT_NAME)
    exp_name = f"mafia_{condition.lower()}_main"
    by_method_view: Dict[str, Dict[str, Dict[str, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for game in selected_games:
        for (view, method_name), vals in compute_game_metrics(game).items():
            if view not in {"Obj", "BYS", "MAF"}:
                continue
            if method_filter is not None and method_name not in method_filter.get(exp_name, set()):
                continue
            by_method_view[method_name][view]["marginal"].append(vals["marginal"])
            by_method_view[method_name][view]["map"].append(vals["map"])

    if by_method_view or method_filter:
        scores["experiments"][exp_name] = {
            "description": f"Mafia-UCB {condition} {SPLIT_NAME} split results",
            "results": {},
        }
        exp_filter = method_filter.get(exp_name, set()) if method_filter is not None else None
        method_names = sorted(exp_filter) if exp_filter else sorted(by_method_view)
        for method_name in method_names:
            method_scores = {}
            for view, metrics in sorted(by_method_view.get(method_name, {}).items()):
                if metrics["marginal"]:
                    method_scores[f"{view}_marginal"] = round(sum(metrics["marginal"]) / len(metrics["marginal"]), 4)
                if metrics["map"]:
                    method_scores[f"{view}_map"] = round(sum(metrics["map"]) / len(metrics["map"]), 4)
            scores["experiments"][exp_name]["results"][method_name] = method_scores

    scores["metadata"]["n_selected_games"] = len(selected_games)
    return scores


def load_method_filter(path: Optional[Path]) -> Optional[Dict[str, Set[str]]]:
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    filters = {}
    for exp_name, exp_data in data.get("experiments", {}).items():
        filters[exp_name] = set(exp_data.get("results", {}).keys())
    return filters


def evaluate(
    results_dir: Path,
    output_path: Path,
    dataset: str = "avalonlogs",
    condition: str = "Truth",
    method_filter_path: Optional[Path] = Path("scoring/scores.json"),
) -> Dict[str, Any]:
    method_filter = load_method_filter(method_filter_path)
    if dataset == "avalonlogs":
        scores = evaluate_avalonlogs(results_dir, dataset, condition, method_filter)
    elif dataset == "avalonnlu":
        scores = evaluate_avalonnlu(results_dir, dataset, condition, method_filter)
    elif dataset == "mafia":
        scores = evaluate_mafia(results_dir, dataset, condition, method_filter)
    else:
        scores = empty_scores(dataset, condition)
        scores["metadata"]["warning"] = "No slice evaluator is implemented for this dataset."

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the visible train slice from pre-generated outputs.")
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dataset", default="avalonlogs", choices=["avalonlogs", "avalonnlu", "mafia"])
    parser.add_argument("--condition", default="Truth", choices=["Truth", "Lie"])
    parser.add_argument(
        "--method-filter",
        type=Path,
        default=Path("scoring/scores.json"),
        help="Scores file whose experiment/method entries define the current method set to score.",
    )
    parser.add_argument("--train-scores", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    method_filter_path = args.train_scores if args.train_scores is not None else args.method_filter

    scores = evaluate(
        results_dir=args.results_dir,
        output_path=args.output,
        dataset=args.dataset,
        condition=args.condition,
        method_filter_path=method_filter_path,
    )
    print(f"Scores written to {args.output}")
    print(f"Slice: {scores.get('metadata', {}).get('slice')}")
    print(f"Experiments: {list(scores.get('experiments', {}).keys())}")


if __name__ == "__main__":
    main()
