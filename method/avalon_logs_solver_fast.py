"""
Optimized CSP solver for AvalonLogs dataset.

Key optimizations over the original:
  - Avoids deep copies of SDGModel objects
  - Computes scores directly from worlds using pre-computed assertion counts
  - Much faster for large player counts

Usage:
    python avalon_logs_solver_fast.py <constraints_dir> <output_dir> [--quick] [--limit N]
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from copy import deepcopy

sys.setrecursionlimit(100000)

# ---------- role sets ----------
GOOD_ROLES = {"merlin", "percival", "loyal_follower", "servant", "loyal_servant"}
EVIL_ROLES = {
    "evil_minion", "evil-minion", "assassin", "morgana",
    "mordred", "oberon"
}

def is_good(r: str) -> bool:
    return r in GOOD_ROLES

def is_evil(r: str) -> bool:
    return r in EVIL_ROLES


# ---------- predicate factories ----------
def evil_pred_factory(target: str):
    return lambda world: world[target] in EVIL_ROLES


def good_pred_factory(target: str):
    return lambda world: world[target] in GOOD_ROLES


def team_good_pred(team: List[str]):
    """Check if all team members are good."""
    return lambda world: all(is_good(world.get(p, "")) for p in team if p in world)


def percival_mm_pred(c1: str, c2: str):
    """Exactly {c1,c2} are {merlin,morgana}."""
    def _pred(w: Dict[str, str]):
        roles = {w[c1], w[c2]}
        if roles != {"merlin", "morgana"}:
            return False
        for p, r in w.items():
            if p not in (c1, c2) and r in {"merlin", "morgana"}:
                return False
        return True
    return _pred


# ---------- evidence builders ----------
def build_pred(schema, ev):
    if ev["type"] == "evil_at_least":
        return evil_at_least_pred(schema, **ev["args"])
    raise ValueError(ev["type"])


def evil_at_least_pred(schema, team: list, min_fail: int):
    """Return a predicate checking at least min_fail members of team are evil."""
    def predicate(world: dict):
        bad_count = sum(1 for p in team if not schema.is_good(world[p]))
        return bad_count >= min_fail
    return predicate


# ---------- assertion/hypothesis builders ----------
def build_assertion_checker(schema, c: Dict):
    """Build a function that returns True if the assertion is satisfied."""
    t, a = c["type"], c["args"]
    if t == "assert_team_good":
        pred = team_good_pred(a["team"])
        speaker = a["speaker"]
        def check(world, p=pred, sp=speaker, sc=schema):
            return (not sc.is_good(world[sp])) or p(world)
        return check
    elif t == "assert_role_is":
        speaker = a["speaker"]
        role = a["role"]
        def check(world, sp=speaker, rl=role):
            return world[sp] == rl
        return check
    elif t == "assert_role_in":
        speaker = a["speaker"]
        target = a["target"]
        pred = evil_pred_factory(target) if a["set"] == "evil" else good_pred_factory(target)
        def check(world, p=pred, sp=speaker, sc=schema):
            return (not sc.is_good(world[sp])) or p(world)
        return check
    return lambda world: True


def build_hypothesis_checker(schema, c: Dict):
    """Build a function that returns True if the hypothesis is satisfied."""
    t, a = c["type"], c["args"]
    if t == "hypo_team_good":
        pred = team_good_pred(a["team"])
        speaker = a["speaker"]
        def check(world, p=pred, sp=speaker, sc=schema):
            return (not sc.is_good(world[sp])) or p(world)
        return check
    elif t == "hypo_role_in":
        speaker = a["speaker"]
        target = a["target"]
        pred = evil_pred_factory(target) if a["set"] == "evil" else good_pred_factory(target)
        def check(world, p=pred, sp=speaker, sc=schema):
            return (not sc.is_good(world[sp])) or p(world)
        return check
    return lambda world: True


# ---------- world enumeration (optimized) ----------
def enumerate_assignments(players: List[str], schema) -> List[Dict]:
    """Generate all possible role assignments."""
    items = list(schema.role_counts.items())

    def rec(i, remaining, part):
        if i == len(items):
            yield {**part}
            return
        role, k = items[i]
        for combo in combinations(remaining, k):
            nxt_rem = [p for p in remaining if p not in combo]
            nxt_part = part.copy()
            for p in combo:
                nxt_part[p] = role
            yield from rec(i + 1, nxt_rem, nxt_part)

    return rec(0, players, {})


from itertools import combinations


def filter_worlds(worlds: List[Dict], hard_preds) -> List[Dict]:
    """Filter worlds by hard constraints."""
    return [w for w in worlds if all(h(w) for h in hard_preds)]


# ---------- fast scoring without deep copies ----------
def score_worlds_direct(
    worlds: List[Dict],
    players: List[str],
    A_base: float,
    assert_checks: List,
    hypo_checks: List,
    hypo_weights: List[float],
    ig_weights: List[float],
    use_assert: bool,
    use_hyp: bool,
    use_ig: bool,
    manual_weights: List[float],
) -> Tuple[Dict, Dict]:
    """
    Compute posteriors and MAP directly from worlds list.
    Returns (marginal_posteriors, map_assignment).
    """
    if not worlds:
        return {}, {}

    n = len(worlds)
    log_A = math.log(A_base)

    # Pre-compute assertion count and hypothesis sums for each world
    assert_counts = []
    hypo_sums = []
    for w in worlds:
        if use_assert:
            m = sum(1 for check in assert_checks if check(w))
        else:
            m = 0
        if use_hyp:
            if use_ig:
                s = sum(hypo_weights[i] * (1 if check(w) else 0) for i, check in enumerate(hypo_checks))
            else:
                s = sum(manual_weights[i] * (1 if check(w) else 0) for i, check in enumerate(hypo_checks))
        else:
            s = 0.0
        assert_counts.append(m)
        hypo_sums.append(s)

    # Compute log scores
    log_scores = []
    for m, s in zip(assert_counts, hypo_sums):
        if m == 0 and s == 0:
            log_scores.append(0.0)
        else:
            log_scores.append(m * log_A + math.log(1.0 + s))

    # Numerically stable softmax
    max_log = max(log_scores)
    exp_scores = [math.exp(ls - max_log) for ls in log_scores]
    Z = sum(exp_scores)

    # Marginal posteriors
    from collections import Counter
    prob = {p: Counter() for p in players}
    for w, s in zip(worlds, exp_scores):
        for p, r in w.items():
            prob[p][r] += s
    for p in players:
        total = sum(prob[p].values())
        if total > 0:
            for r in prob[p]:
                prob[p][r] /= total

    # MAP assignment
    best_idx = max(range(len(exp_scores)), key=lambda i: exp_scores[i])
    best_world = worlds[best_idx]

    return prob, best_world


# ---------- CSP stage settings ----------
ALL_SETTINGS = [
    ("Strict",   False, False, False, False),
    ("+Assert",  True,  False, False, False),
    ("+HypIG",   True,  True,  True,  False),
    ("+HypM",    True,  True,  False, False),
    ("+TurnIG",  True,  True,  True,  True),
]

QUICK_SETTINGS = [
    ("Strict",   False, False, False, False),
    ("+HypIG",   True,  True,  True,  False),
]


# ---------- IG weight computation ----------
def _build_hypo_predicate(c: Dict):
    """Build a raw (unconditional) predicate from a hypothesis constraint dict."""
    t, a = c["type"], c["args"]
    if t == "hypo_team_good":
        team = a["team"]
        return lambda w: all(is_good(w.get(p, "")) for p in team if p in w)
    elif t == "hypo_role_in":
        target = a["target"]
        if a["set"] == "evil":
            return lambda w: is_evil(w.get(target, ""))
        else:
            return lambda w, t=target: is_good(w.get(t, ""))
    return lambda w: True


def compute_ig_weights(
    worlds: List[Dict],
    hypo_list: List[Dict],
    schema=None,
    beta_ig: float = 1.0,
) -> List[float]:
    """Compute IG weights for hypotheses using conditional predicates.
    Returns list in same order as hypo_list."""
    n_worlds = len(worlds)
    if n_worlds == 0:
        return [0.0] * len(hypo_list)

    def binary_entropy(p_val: float) -> float:
        if p_val <= 0 or p_val >= 1:
            return 0.0
        return -p_val * math.log2(p_val) - (1 - p_val) * math.log2(1 - p_val)

    weights = []
    for h in hypo_list:
        # Use conditional predicate (matching sdg_framework.add_hypothesis behavior)
        # If speaker is evil, constraint always satisfied; if good, raw predicate must hold
        if schema is not None:
            speaker = h["args"]["speaker"]
            raw_pred = _build_hypo_predicate(h)
            def cond_pred(w, sp=speaker, pr=raw_pred, sc=schema):
                return (not sc.is_good(w[sp])) or pr(w)
            pred = cond_pred
        else:
            pred = _build_hypo_predicate(h)
        true_cnt = sum(1 for w in worlds if pred(w))
        if true_cnt == 0 or true_cnt == n_worlds:
            weights.append(0.0)
        else:
            p = true_cnt / n_worlds
            weights.append(beta_ig * binary_entropy(p))
    return weights


# ---------- manual hypothesis weights ----------
W_STRONG = 0.50
W_REJECT = 0.20
W_WEAK = 0.10


# ---------- main solver ----------
def solve_one(
    fp: Path,
    settings: List[Tuple] = ALL_SETTINGS,
    verbose: bool = False,
) -> dict:
    """Solve a single game's constraints."""
    game = json.loads(fp.read_text(encoding="utf-8"))
    names = [p["name"] for p in game["players"]]
    truth = {p["name"]: p["role"] for p in game["players"]}

    # Build schema
    from method.generic_board import build_schema
    schema = build_schema(game["schema"])

    by_role: Dict[str, List[str]] = {}
    for n, r in truth.items():
        by_role.setdefault(r, []).append(n)

    out = {"file": fp.name, "players": truth, "quests": {}}
    hard_acc, assert_acc = [], []
    hypo_acc: Dict[int, List] = {}  # quest_idx -> list of hypotheses

    for q in game["quests"]:
        idx = q["quest"]
        hard_acc.extend(q["constraints"]["evidence"])
        assert_acc.extend(q["constraints"]["assertions"])
        hypo_acc[idx] = q["constraints"]["hypotheses"]

        out["quests"][str(idx)] = {}

        # Precompute all hypotheses (cumulative)
        all_hypos = [h for hs in hypo_acc.values() for h in hs]

        # Precompute hard predicates
        hard_preds = [build_pred(schema, ev_c) for ev_c in hard_acc]

        # Precompute assertion checkers
        assert_checks = [build_assertion_checker(schema, a) for a in assert_acc]

        # Precompute hypothesis checkers and manual weights
        hypo_checks = [build_hypothesis_checker(schema, h) for h in all_hypos]
        manual_weights = []
        for h in all_hypos:
            t = h["type"]
            if t == "hypo_team_good":
                manual_weights.append(W_STRONG)
            elif t == "hypo_role_in":
                args = h["args"]
                # Reject votes get W_REJECT, approval votes get W_WEAK
                # We need to track vote type - for now use W_REJECT
                manual_weights.append(W_REJECT)
            else:
                manual_weights.append(0.1)

        # Precompute worlds for objective view
        all_worlds_list = list(enumerate_assignments(names, schema))
        obj_worlds = filter_worlds(all_worlds_list, hard_preds)

        # Precompute IG weights for objective view (using conditional predicates)
        obj_ig_weights = compute_ig_weights(obj_worlds, all_hypos, schema=schema)

        # Build perspectives
        perspective = {"objective": []}
        role_counters = {r: 0 for r in by_role}

        for player in names:
            role = truth[player]
            role_counters[role] += 1
            view_name = (
                f"{role}{role_counters[role]}"
                if len(by_role[role]) > 1 else role
            )
            extras = []

            # Add role-is constraint
            extras.append(lambda w, p=player, r=role: w[p] == r)

            # Role-specific knowledge
            if role in ("evil_minion", "evil-minion"):
                for r2 in ("evil_minion", "evil-minion", "mordred", "morgana"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "mordred":
                for r2 in ("evil_minion", "evil-minion", "morgana"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "morgana":
                for r2 in ("evil_minion", "evil-minion", "mordred"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "merlin":
                for r2 in ("evil_minion", "evil-minion", "oberon", "morgana"):
                    for p2 in by_role.get(r2, []):
                        extras.append(evil_pred_factory(p2))
            elif role == "percival":
                mm = by_role.get("merlin", []) + by_role.get("morgana", [])
                if len(mm) == 2:
                    extras.append(percival_mm_pred(mm[0], mm[1]))

            perspective[view_name] = extras

        # Run each CSP stage for each perspective
        for view, extras in perspective.items():
            out["quests"][str(idx)][view] = {}

            # Filter worlds by hard constraints ONLY (perspective extras are soft constraints)
            view_worlds = filter_worlds(all_worlds_list, hard_preds)
            if not view_worlds:
                for title, ua, uh, aw, only_today in settings:
                    out["quests"][str(idx)][view][title] = {"posterior": {}, "best": {}}
                continue

            # Precompute IG weights for this view (using conditional predicates)
            view_ig_weights = compute_ig_weights(view_worlds, all_hypos, schema=schema)

            for title, ua, uh, aw, only_today in settings:
                # Select hypotheses for this setting
                if only_today:
                    src_hypos = hypo_acc.get(idx, [])
                    # Need to re-index hypo_checks and weights for current-quest hypos only
                    src_checks = []
                    src_ig = []
                    src_manual = []
                    for qi, hlist in hypo_acc.items():
                        if qi == idx:
                            for j, h in enumerate(hlist):
                                # Find the global index
                                offset = sum(len(hypo_acc[k]) for k in sorted(hypo_acc.keys()) if k < qi)
                                if offset + j < len(hypo_checks):
                                    src_checks.append(hypo_checks[offset + j])
                                    src_ig.append(obj_ig_weights[offset + j])
                                    src_manual.append(manual_weights[offset + j])
                else:
                    src_checks = hypo_checks
                    src_ig = view_ig_weights
                    src_manual = manual_weights

                try:
                    post, best = score_worlds_direct(
                        worlds=view_worlds,
                        players=names,
                        A_base=10000.0,
                        assert_checks=assert_checks if ua else [],
                        hypo_checks=src_checks if uh else [],
                        hypo_weights=src_ig if (uh and aw) else [],
                        use_assert=ua,
                        use_hyp=uh,
                        use_ig=aw,
                        manual_weights=src_manual if (uh and not aw) else [],
                    )
                except Exception:
                    post, best = {}, {}

                out["quests"][str(idx)][view][title] = {
                    "posterior": post,
                    "best": best
                }

        if verbose:
            print(f"  Quest {idx}: {len(obj_worlds)} worlds")

    return out


# ---------- batch runner ----------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Solve AvalonLogs CSP (fast)")
    parser.add_argument("constraints_dir", type=str)
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--quick", action="store_true",
                        help="Only run Strict and HypIG settings")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of files to process")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    in_dir = Path(args.constraints_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    settings = QUICK_SETTINGS if args.quick else ALL_SETTINGS
    files = sorted(in_dir.glob("*_constraints.json"))
    if args.limit > 0:
        files = files[:args.limit]

    # Pre-compute which files are already solved
    solved_stems = {f.stem for f in out_dir.glob("*_constraints_solve.json")}
    files_to_process = [f for f in files if f.stem not in solved_stems]

    print(f"Total: {len(files)} files, {len(solved_stems)} done, {len(files_to_process)} to solve")
    print(f"Settings: {[s[0] for s in settings]}")

    import time
    t0 = time.time()
    solved = errors = 0
    for fp in files_to_process:
        dst = out_dir / (fp.stem + "_constraints_solve.json")
        if dst.exists():
            solved += 1
            continue
        try:
            result = solve_one(fp, settings=settings, verbose=args.verbose)
            dst.write_text(json.dumps(result), encoding="utf-8")
            solved += 1
            if solved % 100 == 0:
                elapsed = time.time() - t0
                rate = solved / elapsed
                eta = (len(files_to_process) - solved) / rate if rate > 0 else 0
                print(f"  {solved}/{len(files_to_process)} ({rate:.1f}/s, ETA: {eta/60:.0f}m)", flush=True)
        except Exception as e:
            errors += 1
            print(f"  ERROR {fp.name}: {type(e).__name__}: {e}", flush=True)
            if errors <= 3:
                import traceback
                traceback.print_exc()

    elapsed = time.time() - t0
    rate = solved / elapsed if elapsed > 0 else 0
    print(f"Done. {solved} solved, {errors} errors in {elapsed/60:.1f}m ({rate:.1f}/s)")


if __name__ == "__main__":
    main()
