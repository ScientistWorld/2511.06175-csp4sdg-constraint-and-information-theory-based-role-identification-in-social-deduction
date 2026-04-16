from typing import List

from sdg_framework import RoleSchema

ROLE_COUNTS = {
    "merlin":    1,
    "percival":  1,
    "servant":   2,
    "assassin":  1,
    "morgana":   1
}
GOOD_ROLES = ["merlin", "percival", "servant"]

SCHEMA = RoleSchema(ROLE_COUNTS, GOOD_ROLES)

# ---------- helper predicates ----------
def role_is(player: str, role: str):
    return lambda a, p=player, r=role: a[p] == r

def role_not(player: str, role: str):
    return lambda a, p=player, r=role: a[p] != r

def evil_at_least(team: List[str], k: int):
    EVIL = {"assassin", "morgana"}
    def _pred(a, T=team, K=k):
        return sum(1 for p in T if a[p] in EVIL) >= K
    return _pred

def team_all_good(team: List[str]):
    GOOD = set(GOOD_ROLES)
    return lambda a, T=team: all(a[p] in GOOD for p in T)
