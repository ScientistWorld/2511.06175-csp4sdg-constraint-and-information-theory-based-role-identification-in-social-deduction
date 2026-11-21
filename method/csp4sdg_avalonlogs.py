"""
CSP4SDG reference inference on AvalonLogs evaluation instances.

An instance is one game prefix (completed missions 1..q) seen from one
viewpoint (see briefing/evaluation.md for the schema).  This module implements
the paper's CSP4SDG pipeline for such an instance:

  1. Constraint extraction, as in the paper's AvalonLogs converter
     (official ``batch_convert_structured.py``): a mission with f fail cards
     gives the hard phenomenon ``evil_at_least(team, f)``; every proposal gives
     the hypothesis ``hypo_team_good(proposer, team)`` (w=0.5), every approving
     vote ``hypo_team_good(voter, team)`` (w=0.1) and every rejecting vote
     ``hypo_role_in(voter, random team member, evil)`` (w=0.2).
  2. Viewpoint evidence, as in the official ``batch_solve_structured.py``: the
     viewer's own role is fixed; Merlin and evil roles add "this player is
     evil" for every player they are shown; Percival adds "these two players
     are {Merlin, Morgana}" when both exist.
  3. Exact inference: hard constraints prune worlds, hypotheses score the
     rest with S(a) = 1 + sum_h w_h * [a |= h] (Eq. 1, no assertions exist in
     AvalonLogs), posterior marginals by normalisation (Eq. 2), IG weights
     w_h = H2(fraction of feasible worlds satisfying h) computed on the
     viewpoint's feasible worlds (sdg_framework.add_hypothesis semantics).

Every constraint above depends on roles only through the good/evil side of
each player, except the viewpoint's role-level knowledge.  Inference therefore
enumerates evil subsets and, inside each subset, the role assignments of each
side; this visits exactly the same complete worlds as the role-level
enumeration in ``method/sdg_framework.py`` (checked by
``method/csp4sdg_enumerate.py``) at a fraction of the cost.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import os
import random
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

W_STRONG = 0.50  # proposer trusts their own team
W_REJECT = 0.20  # rejecting voter suspects a team member
W_WEAK = 0.10    # approving voter weakly trusts the team

# Roles a viewer is NOT shown, by the Avalon rules (used only by "full" knowledge).
MERLIN_HIDDEN = {"mordred"}
EVIL_HIDDEN = {"oberon"}


# --------------------------------------------------------------------------
# Constraint extraction
# --------------------------------------------------------------------------

def instance_rng(inst: dict, salt: Optional[str] = None) -> random.Random:
    """Per-instance RNG for the converter's random suspect choice.

    The official converter draws suspects from one global RNG in file order;
    seeding per instance makes each prediction independent of processing order.
    CSP4SDG_SEED only exists to measure seed sensitivity.
    """
    if salt is None:
        salt = "csp4sdg" + os.environ.get("CSP4SDG_SEED", "")
    digest = hashlib.sha256(f"{salt}:{inst['instance_id']}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def extract_constraints(inst: dict, rng: Optional[random.Random] = None):
    """Return (hard, hypotheses) for the instance prefix.

    hard:       list of (team, min_fail)
    hypotheses: list of (kind, speaker, payload, manual_weight) where kind is
                "team_good" (payload = team) or "role_evil" (payload = target).
    """
    if rng is None:
        rng = instance_rng(inst)
    hard: List[Tuple[Tuple[str, ...], int]] = []
    hyps: List[Tuple[str, str, object, float]] = []
    for m in inst["missions"]:
        if m.get("result") in ("SUCCESS", "FAIL") and int(m.get("num_fails", 0)) > 0:
            hard.append((tuple(m["team"]), int(m["num_fails"])))
        for prop in m.get("proposals", []):
            team = tuple(prop["team"])
            if not team:
                continue
            hyps.append(("team_good", prop["proposer"], team, W_STRONG))
            for voter in prop.get("approve", []):
                hyps.append(("team_good", voter, team, W_WEAK))
            for voter in prop.get("reject", []):
                cands = [p for p in team if p != voter]
                if cands:
                    target = rng.choice(sorted(cands))
                    hyps.append(("role_evil", voter, target, W_REJECT))
    return hard, hyps


# --------------------------------------------------------------------------
# Viewpoint knowledge
# --------------------------------------------------------------------------

class Knowledge:
    """Role-level knowledge of one viewpoint."""

    def __init__(self, inst: dict, mode: str = "paper"):
        players = list(inst["players"])
        counts = {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}
        good = set(inst["good_roles"]) & set(counts)
        evil = set(counts) - good
        self.forced: Dict[str, str] = {}
        self.must_evil: set = set()
        self.allowed: Dict[str, set] = {}
        self.pair: Optional[Tuple[str, str]] = None
        view = inst.get("view") or {}
        role = view.get("viewer_role")
        viewer = view.get("viewer")
        if not role or not viewer:
            return
        self.forced[viewer] = role
        if role == "percival":
            cands = list(view.get("merlin_candidates", []))
            if len(cands) == 2:
                self.pair = (cands[0], cands[1])
            elif len(cands) == 1 and mode == "full":
                self.forced[cands[0]] = "merlin"
        elif "sees_evil" in view:
            seen = set(view.get("sees_evil", []))
            self.must_evil |= seen
            if mode == "full":
                hidden = (MERLIN_HIDDEN if role == "merlin" else EVIL_HIDDEN) & evil
                for p in players:
                    if p == viewer:
                        continue
                    if p in seen:
                        self.allowed[p] = evil - hidden
                    else:
                        self.allowed[p] = good | hidden


# --------------------------------------------------------------------------
# Exact grouped inference
# --------------------------------------------------------------------------

def _enum_side(side_players: Sequence[str], counts: Dict[str, int],
               forced: Dict[str, str], allowed: Dict[str, set]):
    """Enumerate distinct role assignments of `counts` to `side_players`.

    Returns (n_assignments, marginal role counts per player, first assignment)
    or (0, None, None) when no assignment is legal.
    """
    counts = dict(counts)
    order = sorted(side_players, key=lambda p: (p not in forced, p))
    total = 0
    marg = {p: Counter() for p in side_players}
    first: Optional[Dict[str, str]] = None
    cur: Dict[str, str] = {}

    def rec(i: int):
        nonlocal total, first
        if i == len(order):
            total += 1
            for p, r in cur.items():
                marg[p][r] += 1
            if first is None:
                first = dict(cur)
            return
        p = order[i]
        if p in forced:
            options = [forced[p]]
        else:
            options = [r for r in counts if counts[r] > 0]
        for r in options:
            if counts.get(r, 0) <= 0:
                continue
            if p in allowed and r not in allowed[p]:
                continue
            counts[r] -= 1
            cur[p] = r
            rec(i + 1)
            del cur[p]
            counts[r] += 1

    rec(0)
    if total == 0:
        return 0, None, None
    return total, marg, first


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def feasible_groups(inst: dict, knowledge: Knowledge, hard=()) -> List[dict]:
    """All evil subsets consistent with hard constraints and viewpoint knowledge.

    Each group carries: mask (evil subset as bitmask), ways (number of complete
    worlds), marg (player -> role -> fraction of those worlds), best (one world).
    """
    players = list(inst["players"])
    ix = {p: i for i, p in enumerate(players)}
    counts = {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}
    good = set(inst["good_roles"]) & set(counts)
    evil_counts = {r: c for r, c in counts.items() if r not in good}
    good_counts = {r: c for r, c in counts.items() if r in good}
    k = sum(evil_counts.values())
    hard_masks = [(sum(1 << ix[p] for p in set(team)), f) for team, f in hard]
    must_mask = sum(1 << ix[p] for p in knowledge.must_evil)

    groups = []
    for combo in itertools.combinations(range(len(players)), k):
        mask = 0
        for i in combo:
            mask |= 1 << i
        if mask & must_mask != must_mask:
            continue
        if any((mask & t).bit_count() < f for t, f in hard_masks):
            continue
        forced = dict(knowledge.forced)
        if knowledge.pair is not None:
            a, b = knowledge.pair
            in_a, in_b = bool(mask >> ix[a] & 1), bool(mask >> ix[b] & 1)
            if in_a == in_b:
                continue
            want_a = "morgana" if in_a else "merlin"
            want_b = "morgana" if in_b else "merlin"
            if forced.get(a, want_a) != want_a or forced.get(b, want_b) != want_b:
                continue
            forced[a] = want_a
            forced[b] = want_b
        ok = True
        for p, r in forced.items():
            if (r in good) == bool(mask >> ix[p] & 1) or r not in counts:
                ok = False
                break
        if not ok:
            continue
        evil_players = [p for p in players if mask >> ix[p] & 1]
        good_players = [p for p in players if not mask >> ix[p] & 1]
        ne, me, fe = _enum_side(evil_players, evil_counts, forced, knowledge.allowed)
        if not ne:
            continue
        ng, mg, fg = _enum_side(good_players, good_counts, forced, knowledge.allowed)
        if not ng:
            continue
        marg = {}
        for p in evil_players:
            marg[p] = {r: c / ne for r, c in me[p].items()}
        for p in good_players:
            marg[p] = {r: c / ng for r, c in mg[p].items()}
        best = dict(fe)
        best.update(fg)
        groups.append({"mask": mask, "ways": ne * ng, "marg": marg, "best": best})
    return groups


def hypothesis_table(inst: dict, hyps) -> List[Tuple[int, int, int, float, int]]:
    """Group identical hypotheses: (kind, speaker_bit, payload_mask, manual_w_sum, multiplicity)."""
    ix = {p: i for i, p in enumerate(inst["players"])}
    table: Dict[Tuple[int, int, int], List[float]] = {}
    for kind, speaker, payload, w in hyps:
        if kind == "team_good":
            key = (0, 1 << ix[speaker], sum(1 << ix[p] for p in set(payload)))
        else:
            key = (1, 1 << ix[speaker], 1 << ix[payload])
        table.setdefault(key, []).append(w)
    return [(k[0], k[1], k[2], sum(ws), len(ws)) for k, ws in table.items()]


def _sat(kind: int, speaker: int, payload: int, mask: int) -> bool:
    """Conditional hypothesis: satisfied if the speaker is evil, else the raw predicate."""
    if mask & speaker:
        return True
    if kind == 0:
        return (mask & payload) == 0
    return (mask & payload) != 0


def posterior_from_scores(players: Sequence[str], groups: List[dict], scores: Sequence[float]):
    z = sum(g["ways"] * s for g, s in zip(groups, scores))
    post = {p: {} for p in players}
    for g, s in zip(groups, scores):
        wgt = g["ways"] * s / z
        if wgt == 0.0:
            continue
        for p, rp in g["marg"].items():
            dst = post[p]
            for r, v in rp.items():
                dst[r] = dst.get(r, 0.0) + wgt * v
    best_j = max(range(len(groups)), key=lambda j: scores[j])
    return post, dict(groups[best_j]["best"])


def ig_scores(groups: List[dict], table) -> List[float]:
    total = sum(g["ways"] for g in groups)
    scores = [1.0] * len(groups)
    for kind, sp, payload, _manual, mult in table:
        sat = [_sat(kind, sp, payload, g["mask"]) for g in groups]
        p = sum(g["ways"] for g, s in zip(groups, sat) if s) / total
        w = _binary_entropy(p) * mult
        if w:
            for j, s in enumerate(sat):
                if s:
                    scores[j] += w
    return scores


def manual_scores(groups: List[dict], table) -> List[float]:
    scores = [1.0] * len(groups)
    for kind, sp, payload, manual, _mult in table:
        for j, g in enumerate(groups):
            if _sat(kind, sp, payload, g["mask"]):
                scores[j] += manual
    return scores


def robust_groups(inst: dict, knowledge: Knowledge, hard) -> Tuple[List[dict], str]:
    """Feasible groups, relaxing constraints only if the data are contradictory."""
    groups = feasible_groups(inst, knowledge, hard)
    if groups:
        return groups, "ok"
    groups = feasible_groups(inst, knowledge, ())
    if groups:
        return groups, "dropped_evidence"
    return feasible_groups(inst, Knowledge({**inst, "view": {}}), ()), "dropped_all"


def _clean(post: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {p: {r: round(v, 10) for r, v in rp.items() if v > 0.0} for p, rp in post.items()}


def solve_instance(inst: dict, settings=("CSP_Strict", "CSP_HypIG"), knowledge_mode: str = "paper") -> dict:
    """Run the requested CSP settings on one instance."""
    hard, hyps = extract_constraints(inst)
    knowledge = Knowledge(inst, knowledge_mode)
    groups, _status = robust_groups(inst, knowledge, hard)
    players = list(inst["players"])
    out = {}
    table = None
    for name in settings:
        if name.endswith("Strict"):
            scores = [1.0] * len(groups)
        else:
            if table is None:
                table = hypothesis_table(inst, hyps)
            scores = manual_scores(groups, table) if name.endswith("HypM") else ig_scores(groups, table)
        post, best = posterior_from_scores(players, groups, scores)
        out[name] = {"posterior": _clean(post), "best": best}
    return out
