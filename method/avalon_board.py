"""
Avalon board-specific predicate factories and schema.

Standard 6-player Avalon setup used in the paper's Avalon-NLU experiments:
  Merlin (1), Percival (1), Servant (2), Assassin (1), Morgana (1)
"""

from typing import List
from method.sdg_framework import RoleSchema

# Standard 6-player Avalon role composition
ROLE_COUNTS = {
    "merlin": 1,
    "percival": 1,
    "servant": 2,
    "assassin": 1,
    "morgana": 1,
}
GOOD_ROLES = ["merlin", "percival", "servant"]

SCHEMA = RoleSchema(ROLE_COUNTS, GOOD_ROLES)

# Extended role sets (used across datasets)
GOOD_ROLE_SET = {"merlin", "percival", "servant", "loyal_follower", "loyal_servant"}
EVIL_ROLE_SET = {"assassin", "morgana", "minion", "mordred", "evil_minion", "evil-minion"}


def is_good(role: str) -> bool:
    return role in GOOD_ROLE_SET


def is_evil(role: str) -> bool:
    return role in EVIL_ROLE_SET


# ---------- predicate factories ----------

def role_is(player: str, role: str):
    """Hard predicate: player has exactly this role."""
    return lambda a, p=player, r=role: a[p] == r


def role_not(player: str, role: str):
    """Hard predicate: player does NOT have this role."""
    return lambda a, p=player, r=role: a[p] != r


def evil_at_least(team: List[str], k: int):
    """Hard predicate: at least k members of the team are evil."""
    def pred(a, T=team, K=k):
        return sum(1 for p in T if is_evil(a[p])) >= K
    return pred


def team_all_good(team: List[str]):
    """Hard predicate: all team members are good."""
    def pred(a, T=team):
        return all(is_good(a[p]) for p in T)
    return pred


def percival_mm_pred(cand1: str, cand2: str):
    """
    Hard predicate for Percival's knowledge: exactly {cand1, cand2} are
    {merlin, morgana} in some order, and no other player is merlin/morgana.
    """
    def _pred(a):
        roles = {a[cand1], a[cand2]}
        if roles != {"merlin", "morgana"}:
            return False
        for p, r in a.items():
            if p not in (cand1, cand2) and r in {"merlin", "morgana"}:
                return False
        return True
    return _pred


# ---------- MAP helper ----------

def compute_map(model):
    """Compute MAP assignment for a model."""
    import math
    best, score = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s = sum(sa.weight for sa in model.add_soft if sa.func(w))
        val = m * math.log(model.A_base) + math.log(1 + s)
        if val > score:
            best, score = w, val
    return best
