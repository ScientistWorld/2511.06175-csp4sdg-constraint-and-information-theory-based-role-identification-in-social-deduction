"""
Optimized CSP solver for AvalonLogs dataset.

Key optimizations over the original:
  - Caches world enumeration after hard constraints are applied
  - Computes IG weights in a single pass over hypotheses
  - Reduces redundant model copies
  - Supports --quick flag for faster runs (Strict + HypIG only)

Usage:
    python avalon_logs_solver.py <constraints_dir> <output_dir> [--quick] [--limit N]
"""

import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

import method.sdg_framework as sdg_framework
from method.sdg_framework import SDGModel, enumerate_assignments
import method.generic_board as gb

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
        return gb.evil_at_least(schema, **ev["args"])
    raise ValueError(ev["type"])


def add_assert(model: SDGModel, c: Dict, schema):
    t, a = c["type"], c["args"]
    if t == "assert_team_good":
        model.add_assertion(a["speaker"], gb.team_all_good(schema, a["team"]))
    elif t == "assert_role_is":
        model.add_assertion(a["speaker"], gb.role_is(a["speaker"], a["role"]))
    elif t == "assert_role_in":
        pred = evil_pred_factory(a["target"]) if a["set"] == "evil" else good_pred_factory(a["target"])
        model.add_assertion(a["speaker"], pred)


def add_hypo(
    model: SDGModel,
    c: Dict,
    schema,
    weight_override: Optional[float] = None,
):
    t, a = c["type"], c["args"]
    w = weight_override if weight_override is not None else c.get("weight", 0.2)
    if t == "hypo_team_good":
        model.add_hypothesis(a["speaker"], gb.team_all_good(schema, a["team"]), weight=w, auto_weight=False)
    elif t == "hypo_role_in":
        pred = evil_pred_factory(a["target"]) if a["set"] == "evil" else good_pred_factory(a["target"])
        model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=False)


# ---------- MAP helper ----------
def compute_map(model: SDGModel):
    best, score = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s_sum = sum(sa.weight for sa in model.add_soft if sa.func(w))
        val = m * math.log(model.A_base) + math.log(1 + s_sum)
        if val > score:
            best, score = w, val
    return best


# ---------- precompute IG weights ----------
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
            return lambda w: is_good(w.get(target, ""))
    return lambda w: True


def compute_all_ig_weights(
    worlds: List[Dict],
    hypo_list: List[Dict],
    beta_ig: float = 1.0,
) -> Dict[int, float]:
    """
    Precompute IG weight for each hypothesis using binary entropy.
    Returns a dict mapping id(constraint) -> IG weight.
    """
    n_worlds = len(worlds)
    if n_worlds == 0:
        return {id(h): 0.0 for h in hypo_list}

    def binary_entropy(p_val: float) -> float:
        if p_val <= 0 or p_val >= 1:
            return 0.0
        return -p_val * math.log2(p_val) - (1 - p_val) * math.log2(1 - p_val)

    ig_weights = {}
    for h in hypo_list:
        pred = _build_hypo_predicate(h)
        true_cnt = sum(1 for w in worlds if pred(w))
        if true_cnt == 0 or true_cnt == n_worlds:
            ig_weights[id(h)] = 0.0
        else:
            p = true_cnt / n_worlds
            ig_weights[id(h)] = beta_ig * binary_entropy(p)

    return ig_weights


# ---------- CSP stage settings ----------
# (name, use_assert, use_hyp, auto_weight, only_today)
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
    schema = gb.build_schema(game["schema"])

    by_role: Dict[str, List[str]] = {}
    for n, r in truth.items():
        by_role.setdefault(r, []).append(n)

    out = {"file": fp.name, "players": truth, "quests": {}}
    hard_acc, assert_acc, hypo_acc = [], [], {}

    for q in game["quests"]:
        idx = q["quest"]
        hard_acc.extend(q["constraints"]["evidence"])
        assert_acc.extend(q["constraints"]["assertions"])
        hypo_acc[idx] = q["constraints"]["hypotheses"]

        out["quests"][str(idx)] = {}

        # Precompute all hypotheses (cumulative)
        all_hypos = [h for hs in hypo_acc.values() for h in hs]

        # Precompute worlds for objective view (after hard constraints)
        obj_model = SDGModel(names, deepcopy(schema))
        for ev_c in hard_acc:
            obj_model.add_evidence(build_pred(schema, ev_c))
        obj_worlds = obj_model._worlds()

        # Precompute IG weights once for the objective view
        obj_ig_weights = compute_all_ig_weights(obj_worlds, all_hypos)

        # Build perspective extras for each view
        perspective = {"objective": []}
        role_counters = {r: 0 for r in by_role}

        for player in names:
            role = truth[player]
            role_counters[role] += 1
            view_name = (
                f"{role}{role_counters[role]}"
                if len(by_role[role]) > 1 else role
            )
            extras = [gb.role_is(player, role)]

            # role-specific knowledge
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

            # Build base model for this view
            base = SDGModel(names, deepcopy(schema))
            for ev_c in hard_acc:
                base.add_evidence(build_pred(schema, ev_c))
            for ex in extras:
                base.add_evidence(ex)

            # Precompute worlds and IG weights for this view
            view_worlds = base._worlds()
            view_ig_weights = compute_all_ig_weights(view_worlds, all_hypos)

            for title, ua, uh, aw, only_today in settings:
                model = deepcopy(base)
                if ua:
                    for a in assert_acc:
                        add_assert(model, a, schema)
                if uh:
                    src = hypo_acc[idx] if only_today else all_hypos
                    for h in src:
                        w_override = view_ig_weights.get(id(h)) if aw else None
                        add_hypo(model, h, schema, weight_override=w_override)

                try:
                    if not ua and not uh:
                        post = model.evaluate_hard_only()[0]
                    else:
                        post = model.evaluate_advanced()[0]
                    best = compute_map(model)
                except ValueError:
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
    parser = argparse.ArgumentParser(description="Solve AvalonLogs CSP")
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

    print(f"Solving {len(files)} files with {[s[0] for s in settings]}")

    solved = 0
    errors = 0
    import time
    t0 = time.time()
    for fp in files:
        dst = out_dir / (fp.stem + "_solve.json")
        if dst.exists():
            solved += 1
            continue
        try:
            result = solve_one(fp, settings=settings, verbose=args.verbose)
            dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
            solved += 1
            if solved % 100 == 0:
                elapsed = time.time() - t0
                rate = solved / elapsed
                eta = (len(files) - solved) / rate if rate > 0 else 0
                print(f"  {solved}/{len(files)} ({rate:.1f}/s, ETA: {eta/60:.0f}m)")
        except Exception as e:
            errors += 1
            print(f"  ERROR {fp.name}: {type(e).__name__}: {e}")
            if errors <= 3:
                import traceback
                traceback.print_exc()

    elapsed = time.time() - t0
    print(f"Done. {solved} solved, {errors} errors in {elapsed/60:.1f}m ({solved/elapsed:.1f}/s)")


if __name__ == "__main__":
    main()
