"""
CSP4SDG: Core framework — generic Social-Deduction Game CSP solver.

Based on the paper: "CSP4SDG: Constraint and Information-Theory Based Role
Identification in Social Deduction Games with LLM-Enhanced Inference" (AAAI 2026).

This module contains the CSP solver that:
  * Enumerates all valid role assignments satisfying hard constraints
  * Scores assignments using multiplicative assertions and additive hypotheses
  * Supports information-gain (IG) automatic weighting for hypotheses
  * Computes marginal posteriors and MAP (maximum-a-posteriori) assignments
"""

import itertools
import math
import uuid
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Callable, Dict, List, Optional, Tuple


# ------------------------------------------------------------------
# Role schema
# ------------------------------------------------------------------

class RoleSchema:
    """Describes the role composition of a game."""

    def __init__(self, role_counts: Dict[str, int], good_roles: List[str]):
        self.role_counts = role_counts  # role_key -> count
        self.good_roles = set(good_roles)

    def is_good(self, role: str) -> bool:
        return role in self.good_roles


# ------------------------------------------------------------------
# Assignment enumeration
# ------------------------------------------------------------------

def enumerate_assignments(players: List[str], schema: RoleSchema):
    """
    Generate all possible role assignments for the given players.
    Each assignment is a dict: {player_name -> role_key}
    """
    items = list(schema.role_counts.items())

    def rec(i, remaining, part):
        if i == len(items):
            yield {**part}
            return
        role, k = items[i]
        for combo in itertools.combinations(remaining, k):
            nxt_rem = [p for p in remaining if p not in combo]
            nxt_part = part.copy()
            for p in combo:
                nxt_part[p] = role
            yield from rec(i + 1, nxt_rem, nxt_part)

    return rec(0, players, {})


# ------------------------------------------------------------------
# Constraint types
# ------------------------------------------------------------------

HardConstraint = Callable[[Dict[str, str]], bool]


class SoftMul:
    """Multiplicative soft constraint (assertion)."""

    def __init__(self, func: HardConstraint):
        self.func = func


class SoftAdd:
    """Additive soft constraint (hypothesis)."""

    def __init__(self, func: HardConstraint, weight: float):
        self.func = func
        self.weight = weight


# ------------------------------------------------------------------
# Main CSP model
# ------------------------------------------------------------------

class SDGModel:
    """
    Probabilistic CSP model for social-deduction role inference.

    Supports:
      - Hard evidence/phenomenon constraints that prune invalid assignments
      - Multiplicative soft constraints (assertions) with high weight
      - Additive soft constraints (hypotheses) with manual or IG-computed weight
      - Exact enumeration of all feasible worlds (for n <= 10 players)
    """

    def __init__(
        self,
        players: List[str],
        schema: RoleSchema,
        A_base: float = 10000.0,
        beta_ig: float = 1.0,
        ig_mode: str = "binary_entropy",
    ):
        self.players = players
        self.schema = schema
        self.A_base = A_base  # multiplicative base for assertions
        self.beta_ig = beta_ig  # IG scale factor
        self.ig_mode = ig_mode  # "binary_entropy" or "entropy_drop"
        self.hard: List[HardConstraint] = []
        self.mul_soft: List[SoftMul] = []
        self.add_soft: List[SoftAdd] = []
        self.assertions = defaultdict(list)

    # ---------- registration ----------

    def add_evidence(self, hc: HardConstraint):
        self.hard.append(hc)

    def add_phenomenon(self, hc: HardConstraint):
        self.hard.append(hc)

    def add_assertion(self, speaker: str, predicate: HardConstraint):
        """Add an assertion: conditional on speaker being good, must satisfy predicate."""
        def cond(a, sp=speaker, pr=predicate, sc=self.schema):
            return (not sc.is_good(a[sp])) or pr(a)
        self.mul_soft.append(SoftMul(cond))
        self.assertions[speaker].append(predicate)

    def add_hypothesis(
        self,
        speaker: str,
        predicate: HardConstraint,
        weight: Optional[float] = None,
        auto_weight: bool = False,
    ):
        """Add a hypothesis with optional auto-weighting via information gain."""
        def cond(a, sp=speaker, pr=predicate, sc=self.schema):
            return (not sc.is_good(a[sp])) or pr(a)

        if auto_weight:
            weight = self._compute_ig_weight(cond)
        if weight is None:
            weight = 0.5
        self.add_soft.append(SoftAdd(cond, weight))

    # ---------- world enumeration ----------

    def _worlds(self):
        worlds = list(enumerate_assignments(self.players, self.schema))
        return [w for w in worlds if all(h(w) for h in self.hard)]

    # ---------- evaluation ----------

    def evaluate_hard_only(self) -> Tuple[Dict, Dict, List[Dict]]:
        """
        Evaluate using only hard constraints.
        Returns: (marginal_posteriors, entropy_per_player, feasible_worlds)
        """
        worlds = self._worlds()
        tot = len(worlds)
        prob = {p: Counter() for p in self.players}
        for w in worlds:
            for p, r in w.items():
                prob[p][r] += 1 / tot
        ent = {
            p: -sum(v * math.log2(v) for v in prob[p].values() if v)
            for p in self.players
        }
        return prob, ent, worlds

    def evaluate_advanced(self) -> Tuple[Dict, Dict, List[Dict]]:
        """
        Evaluate with soft constraints (assertions + hypotheses).
        Uses numerically-stable log-space computation.
        Returns: (marginal_posteriors, entropy_per_player, feasible_worlds)
        """
        worlds = self._worlds()
        log_scores = []
        for w in worlds:
            m = sum(1 for pr in self.mul_soft if pr.func(w))
            s = sum(sa.weight for sa in self.add_soft if sa.func(w))
            log_F = m * math.log(self.A_base) + math.log(1.0 + s)
            log_scores.append(log_F)

        max_log = max(log_scores)
        exp_scores = [math.exp(l - max_log) for l in log_scores]
        Z = sum(exp_scores)

        prob = {p: Counter() for p in self.players}
        for w, s in zip(worlds, exp_scores):
            for p, r in w.items():
                prob[p][r] += s
        for p in self.players:
            for r in prob[p]:
                prob[p][r] /= Z

        ent = {
            p: -sum(v * math.log2(v) for v in prob[p].values() if v)
            for p in self.players
        }
        return prob, ent, worlds

    # ---------- MAP assignment ----------

    def map_assignment(self) -> Dict[str, str]:
        """Return the maximum-a-posteriori role assignment."""
        best, score = {}, -math.inf
        for w in self._worlds():
            m = sum(1 for s in self.mul_soft if s.func(w))
            s = sum(sa.weight for sa in self.add_soft if sa.func(w))
            val = m * math.log(self.A_base) + math.log(1 + s)
            if val > score:
                best, score = w, val
        return best

    # ---------- information gain ----------

    def _compute_ig_weight(self, soft_pred: HardConstraint) -> float:
        worlds = self._worlds()
        tot = len(worlds)
        if tot == 0:
            return 0.0

        true_worlds = [w for w in worlds if soft_pred(w)]
        true_cnt = len(true_worlds)
        if true_cnt == 0 or true_cnt == tot:
            return 0.0

        def binary_entropy(p_val: float) -> float:
            if p_val <= 0 or p_val >= 1:
                return 0.0
            return -p_val * math.log2(p_val) - (1 - p_val) * math.log2(1 - p_val)

        def role_entropy(world_list: List[Dict[str, str]]) -> float:
            counts = {p: Counter() for p in self.players}
            total_worlds = len(world_list)
            for w in world_list:
                for player, role in w.items():
                    counts[player][role] += 1
            ent = 0.0
            for player in self.players:
                for c in counts[player].values():
                    prob = c / total_worlds
                    ent -= prob * math.log2(prob)
            return ent

        p = true_cnt / tot
        if self.ig_mode == "entropy_drop":
            prior = role_entropy(worlds)
            posterior = role_entropy(true_worlds)
            ig = max(prior - posterior, 0.0)
        else:
            ig = binary_entropy(p)

        return self.beta_ig * ig

    def set_ig_mode(self, mode: str):
        """Switch between IG heuristics."""
        if mode not in {"binary_entropy", "entropy_drop"}:
            raise ValueError(f"Unsupported IG mode: {mode}")
        self.ig_mode = mode
