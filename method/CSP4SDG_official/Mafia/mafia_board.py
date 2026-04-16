from typing import List

from sdg_framework import RoleSchema

def build_schema(players: List[dict]) -> RoleSchema:
    """
    Build a RoleSchema from players list in constraints.json:
      [{"name":"Nicolas Cole","role":"mafioso"}, ...]
    """
    counts = {}
    for p in players:
        r = p["role"]
        counts[r] = counts.get(r, 0) + 1
    # Good side is 'bystander'
    return RoleSchema(counts, good_roles=["bystander"])


# ---- reusable predicates --------------------------------------------------
def role_is(player: str, role: str):
    return lambda a, p=player, r=role: a[p] == r

def role_not(player: str, role: str):
    return lambda a, p=player, r=role: a[p] != r

def mafia_at_least(team: List[str], k: int = 1):
    return lambda a, T=team, K=k: sum(a[x] == "mafioso" for x in T) >= K
