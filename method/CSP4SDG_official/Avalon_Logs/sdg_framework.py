# Generic Social-Deduction Game engine with:
#   * Hard filtering
#   * Multiplicative assertion weighting
#   * Additive hypothesis weighting
#   * Optional information-gain auto weights

import itertools, math
from collections import Counter, defaultdict
from typing import Dict, List, Callable, Tuple

# ---------- Role schema ----------
class RoleSchema:
    def __init__(self, role_counts: Dict[str, int], good_roles: List[str]):
        self.role_counts = role_counts
        self.good_roles  = set(good_roles)

    def is_good(self, role: str) -> bool:
        return role in self.good_roles


# ---------- enumeration of assignments ----------
def enumerate_assignments(players: List[str], schema: RoleSchema):
    items = list(schema.role_counts.items())

    def rec(i, rem, part):
        if i == len(items):
            yield dict(part)
            return
        role, k = items[i]
        for combo in itertools.combinations(rem, k):
            nxt_rem = [p for p in rem if p not in combo]
            nxt_part = part.copy()
            for p in combo:
                nxt_part[p] = role
            yield from rec(i + 1, nxt_rem, nxt_part)

    return rec(0, players, {})


# ---------- predicate types ----------
HardConstraint = Callable[[Dict[str, str]], bool]


class SoftMul:      # assertion
    def __init__(self, func: HardConstraint):
        self.func = func


class SoftAdd:      # hypothesis
    def __init__(self, func: HardConstraint, weight: float):
        self.func   = func
        self.weight = weight


# ---------- model ----------
class SDGModel:
    def __init__(
        self,
        players: List[str],
        schema: RoleSchema,
        A_base: float = 10000.0,
        beta_ig: float = 1.0,
        ig_mode: str = "binary_entropy",
    ):
        self.players  = players
        self.schema   = schema
        self.A_base   = A_base      # multiplicative base for assertions
        self.beta_ig  = beta_ig     # IG scale
        self.ig_mode  = ig_mode     # "binary_entropy" (default) or "entropy_drop"
        self.hard: List[HardConstraint] = []
        self.mul_soft: List[SoftMul] = []
        self.add_soft: List[SoftAdd] = []
        self.assertions = defaultdict(list)

    # ---------------- registration ----------------
    def add_evidence(self, hc: HardConstraint):
        self.hard.append(hc)

    def add_phenomenon(self, hc: HardConstraint):
        self.hard.append(hc)

    def add_assertion(self, speaker: str, predicate: HardConstraint):
        # conditional: good speaker must satisfy predicate
        def cond(a, sp=speaker, pr=predicate, sc=self.schema):
            return (not sc.is_good(a[sp])) or pr(a)
        self.mul_soft.append(SoftMul(cond))
        self.assertions[speaker].append(predicate)

    def add_hypothesis(self, speaker: str, predicate: HardConstraint, weight: float | None = None, auto_weight: bool = False):
        # conditional wrapper
        def cond(a, sp=speaker, pr=predicate, sc=self.schema):
            return (not sc.is_good(a[sp])) or pr(a)

        if auto_weight:
            weight = self._compute_ig_weight(cond)
        if weight is None:
            weight = 0.5
        self.add_soft.append(SoftAdd(cond, weight))

    # ---------------- evaluation ----------------
    def _worlds(self):
        worlds = list(enumerate_assignments(self.players, self.schema))
        return [w for w in worlds if all(h(w) for h in self.hard)]

    def evaluate_hard_only(self):
        worlds = self._worlds()
        tot = len(worlds)
        prob = {p: Counter() for p in self.players}
        for w in worlds:
            for p, r in w.items():
                prob[p][r] += 1 / tot
        ent = {p: -sum(v * math.log2(v) for v in prob[p].values() if v) for p in self.players}
        return prob, ent, worlds

    def evaluate_advanced(self):
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
        ent = {p: -sum(v * math.log2(v) for v in prob[p].values() if v) for p in self.players}
        return prob, ent, worlds

    # ---------------- IG helper ----------------
    def _compute_ig_weight(self, soft_pred: HardConstraint):
        worlds = self._worlds()
        tot = len(worlds)
        if tot == 0:
            return 0.0
        true_worlds = [w for w in worlds if soft_pred(w)]
        true_cnt = len(true_worlds)
        if true_cnt == 0 or true_cnt == tot:
            return 0.0

        def binary_entropy(p_val: float) -> float:
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
        if mode not in {"binary_entropy", "entropy_drop"}:
            raise ValueError(f"Unsupported IG mode: {mode}")
        self.ig_mode = mode
