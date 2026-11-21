# Paper's Method: CSP4SDG

## Key Contribution

CSP4SDG: A **Constraint Satisfaction Problem (CSP)** framework for role inference in Social Deduction Games. It decomposes game information into four linguistically-agnostic constraint types, then uses a probabilistic CSP solver with information-gain weighting to compute calibrated role posteriors.

## Approach

### Four Constraint Types

1. **Evidence (hard)**: Absolutely true facts — e.g., the assassin's target was Merlin, a night-kill victim is bystander
2. **Phenomenon (hard)**: Aggregate constraints from game events — e.g., at least one evil on a failed quest team
3. **Assertions (soft, high weight)**: Player claims treated as likely true — e.g., "I am Percival", "this team is clean"
4. **Hypotheses (soft, low weight)**: Weaker speculative statements — e.g., "X looks evil" from votes or chat

### CSP-Based Inference

The framework formulates role assignment as a constraint satisfaction problem:
- Variables: each player's role
- Hard constraints (E ∪ P): prune infeasible assignments
- Soft constraints (A ∪ H): score remaining assignments

**Scoring function**: For an assignment $a$:
$$S(a) = \left(\prod_{c \in A, a \models c} w_A\right) \cdot \left(1 + \sum_{h \in H, a \models h} w_H(h)\right)$$

where $w_A \gg 1$ is a high assertion weight, and $w_H(h)$ are hypothesis weights.

**Posterior**: $\Pr(a | \mathcal{C}_t) = S(a) / \sum_{a' \in AS_t} S(a')$

### Information-Gain Weighting

Rather than hand-tuning hypothesis weights, the paper computes Information Gain (IG) for each hypothesis as the entropy reduction when incorporating it. This automatically down-weights noisy hypotheses and up-weights informative ones.

### Three Inference Methods

1. **CSP-only**: Pure constraint-based inference
2. **LLM-only**: Prompt the LLM directly with dialogue history
3. **LLM+CSP**: Augment LLM prompts with CSP posteriors as auxiliary input

## Main Claims

1. CSP-based methods (with proper constraint modeling) consistently outperform LLM-only approaches in role identification accuracy
2. Information-gain auto-weighting for hypotheses is near-optimal vs. hand-tuned weights
3. The hybrid LLM+CSP approach adds modest value to LLMs but the CSP remains the dominant component
4. Pure LLMs struggle with combinatorial reasoning even with large model scale

## Implementation in this gym

- `method/csp4sdg_avalonlogs.py` (called by `scripts/predict.sh` through
  `method/predict.py`) runs CSP4SDG on each instance:
  1. constraint extraction as in the paper's AvalonLogs converter: a quest with
     f fail cards gives `evil_at_least(team, f)`; each proposal gives
     `hypo_team_good(proposer, team)` (w=0.5), each approving vote
     `hypo_team_good(voter, team)` (w=0.1), each rejecting vote
     `hypo_role_in(voter, random other team member, evil)` (w=0.2);
  2. viewpoint evidence as in the official solver: own role fixed; Merlin and
     evil roles add "player is evil" for every player in `sees_evil`; Percival
     adds "these two are {Merlin, Morgana}" when both exist;
  3. exact inference (Eq. 1–3): hard pruning, S(a) = 1 + sum of IG weights of
     satisfied hypotheses, IG = binary entropy of the fraction of the view's
     feasible worlds satisfying the (speaker-conditional) hypothesis.
- All constraints depend on roles only through each player's side, apart from
  the viewpoint's role-level knowledge, so inference enumerates evil subsets
  and the role assignments inside each side. `method/csp4sdg_enumerate.py`
  (literal enumeration with `method/sdg_framework.py`) gives the same posteriors
  to 5e-11.
- Emitted methods: `CSP_Strict` (hard constraints only) and `CSP_HypIG`
  (+ IG-weighted hypotheses). AvalonLogs has no assertions, so `+Assert`
  equals `Strict`.
- Departures from the official code: the random suspect for a rejecting vote is
  drawn per instance (seeded by the instance id) instead of from one global RNG
  in file order, and never the voter themself; `sees_evil` lists all players the
  rules reveal (the official code omitted the rare explicit `assassin` role).
  As in the official code, the viewpoint evidence uses only "listed players are
  evil", not the completeness of the lists.
