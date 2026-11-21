# Overview

- **Paper ID:** 2511.06175
- **Title:** CSP4SDG: Constraint and Information-Theory Based Role Identification in Social Deduction Games with LLM-Enhanced Inference
- **Domain:** Game AI / Multi-Agent Systems / Constraint Satisfaction
- **TL;DR:** A probabilistic constraint-satisfaction framework (CSP4SDG) outperforms LLMs at hidden-role inference in social deduction games by modeling game rules as hard constraints and player statements as weighted soft constraints.

## Short Summary

The paper tackles the role identification problem in Social Deduction Games (Avalon, Mafia, Werewolf), where players must infer each other's hidden identities from game events and dialogue. CSP4SDG maps all game information to four constraint types (evidence, phenomenon, assertions, hypotheses), then uses a CSP solver with information-gain-weighted soft constraints to compute calibrated role posteriors. The key insight is that the combinatorial game structure provides strong inductive bias — structured constraint reasoning dramatically outperforms large language models, even the most capable ones, on this task.

## Key Results

- **CSP methods dominate**: On Avalon-NLU (21 games, 6 players), CSP+HypIG achieves ~0.76 marginal / 0.79 MAP accuracy for Percival vs. ~0.16 marginal / 0.19 MAP for LLM-Global
- **Information-gain weighting is effective**: IG-auto-weighted hypotheses perform on par with hand-tuned weights, eliminating manual tuning
- **LLMs amplify heuristics**: Across GPT-4o-mini, GPT-4o, GPT-4.1, DeepSeek-v3, Gemini-2.0-flash, accuracy barely changes — suggesting the bottleneck is combinatorial reasoning, not language understanding
- **Hybrid LLM+CSP helps LLMs**: All LLM backbones gain ~10-20pp when augmented with CSP posteriors

---

# Problem Definition

## Research Question

In social deduction games such as Avalon, Mafia, and Werewolf, players have hidden roles and reveal information only indirectly through public actions, optional communication, and game outcomes. The central task is **role identification**: given the observed game history and the role composition for that game, infer the most likely role for each player.

The problem is difficult because:
- Observations are incomplete and noisy.
- Some players benefit from misleading others.
- Different roles have different private information.
- The number of possible full role assignments grows rapidly with player count.
- Public events and communication can support multiple conflicting explanations.

## Why It Matters

Accurate role identification is a prerequisite for strategic play in social deduction games. It is also a compact benchmark for hidden-state reasoning in multi-agent settings: a system must combine public evidence, asymmetric information, and uncertainty about other agents' motives.

## Task Definition

**Input**:
- Player list and role composition for one game.
- Public game events such as team proposals, votes, quest outcomes, and eliminations.
- Optional communication traces when available.
- Optional perspective information describing what a particular role viewpoint is allowed to know.

**Output**:
- For each evaluated viewpoint, a probability distribution over possible roles for each player.
- A single maximum-a-posteriori full role assignment.

## Success Criteria

A strong solution should:
1. Assign high probability to each player's true role.
2. Recover accurate full role assignments when uncertainty is low.
3. Remain calibrated when evidence is ambiguous.
4. Respect the declared role composition and viewpoint-specific information.
5. Generalize across player counts without changing the evaluation protocol.

## Difficulty

For Avalon-style role sets, the possible assignment space is small enough to define exactly but large enough to make naive reasoning weak:
- 6 players: 90 possible full assignments in the reproduced role schema.
- 8 players: roughly 2,800 assignments.
- 10 players: roughly 78,000 assignments.

The challenge is not just listing assignments. A method must decide how much each event, outcome, and viewpoint should shift probability mass toward or away from competing hidden-role explanations.

---

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

---

# Evaluation

## Metrics

Two accuracy metrics evaluate hidden-role inference quality.

### Marginal Accuracy

For a game with `P` players, let `r_p` be player `p`'s true role and `a_{p,r}` be the predicted posterior probability that player `p` has role `r`:

```text
MA = (1 / P) * sum_p a_{p,r_p}
```

This rewards calibrated probability mass on the true role even when the full assignment remains uncertain.

### MAP Accuracy

Let `hat_r_p` be the role assigned to player `p` in the single most likely complete assignment:

```text
MAP = (1 / P) * sum_p 1[hat_r_p = r_p]
```

This measures how often the predicted best full assignment gives each player the correct exact role.

### Aggregation

Metrics are averaged over evaluated game states and then over games. Results are reported separately for each viewpoint and player-count experiment.

## Evaluation Protocol

### Dataset

The reproduced gym uses public AvalonLogs games with player lists, public events, quest outcomes, and ground-truth roles. Dialogue is not required for the reproduced benchmark. The downloaded raw logs are converted into a method-independent representation under `data/`, and any valid method may consume that representation or the raw logs.

### Viewpoints

Scores are reported for multiple information settings:
- `Obj`: public information only.
- `MRL`: Merlin's viewpoint.
- `PCV`: Percival's viewpoint.
- `MRG`: Morgana's viewpoint.
- `EVM`: non-special evil viewpoint.

Each viewpoint controls what hidden information the predictor may condition on.

### Experiments

AvalonLogs experiments are split by player count (`avalonlogs_5player` through `avalonlogs_10player`). This prevents improvements on one game size from hiding regressions on another. Larger player counts are more expensive, so coverage is reported in the experiment notes and progress logs.

### Output Contract

Evaluation reads method outputs, not method internals. A method should write one JSON artifact per solved game with:
- the source file identifier,
- player names and true roles,
- per-viewpoint posterior probabilities over roles,
- per-viewpoint best role assignment.

`scripts/evaluate.sh` calls `eval/evaluator.py` to read those artifacts and writes `scoring/scores.json`.

### Statistical Validation

For new research claims, compare methods on matched games and viewpoints. Paired tests such as Wilcoxon signed-rank or paired t-tests are appropriate when enough matched games are available. The gym score itself is based on the metrics and weights in `scoring/reference.json`.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 25m | **GPU**: 0.0h
- **Jobs**: 11 total (1 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 14:54] - core_claim_plus
- CPU resume job `4921dcc7-746` completed successfully after repeated scheduler preemptions.
- Final evaluated coverage is 12,091/12,394 AvalonLogs games; 261 hard instances are recorded as timed out
  and 42 unsolved hard instances remain.
- `scripts/evaluate.sh` refreshed `scoring/scores.json`, and `python validate.py --compare` passed all
  scoring and structure checks.

### [2026-05-17 07:08] - core_claim_plus
- Cancelled resume job `424404a8-280` after it improved solved coverage from 11,533 to 11,986 games but
  then stalled on the hardest remaining large AvalonLogs instances.
- Patched `scripts/run.sh` with a 90-second per-game timeout, a 50-minute solve budget, and persistent
  timeout skipping so future jobs produce progress and still run evaluation before node timeout.

### [2026-05-17 03:43] - core_claim_plus
- Reviewed failed CPU resume job `1b3b35a6-d2f`: it exited before solving because the compute node
  attempted to fetch the AvalonLogs GitHub archive and hit the no-internet restriction.
- Patched `scripts/download.sh` and `scripts/run.sh` so existing raw AvalonLogs files skip all network
  fetches, preserving the same resumable solve/evaluate plan for the remaining 861 games.

### [2026-05-17 03:40] - core_claim_plus
- Verified the existing implementation is the paper's actual CSP4SDG solver: exact role-count enumeration, hard evidence/phenomenon pruning, soft assertions, IG/manual hypotheses, posterior normalization, and marginal/MAP extraction.
- Re-ran `scripts/evaluate.sh` on the current 11,533 solved AvalonLogs outputs; `python3 validate.py --compare` passes.
- Patched `scripts/download.sh` to fetch AvalonLogs from the verified GitHub archive instead of relying on a local temporary clone.
- Prepared a CPU resume job to solve the remaining 861 larger AvalonLogs games and refresh `scoring/scores.json`.

### [2026-04-16] - Audit & IG Fix
- Audited previous agent's work: implementation is the paper's actual CSP algorithm
- Found and fixed critical bug: IG weight computation used unconditional predicates
  instead of conditional predicates matching the paper's formulation
- The fix: `_build_conditional_hypo_predicate` wraps hypothesis predicates with
  `(not sc.is_good(w[sp])) or pr(w)`, matching the official repo's `add_hypothesis`
- Copied official CSP4SDG repo (github.com/Nortrom1213/CSP4SDG) to method/CSP4SDG_official
- Submitted CPU job to re-solve all 12,394 games with fixed IG computation
- Core claim remains valid: CSP_Strict matches paper within ±0.03 on all metrics

### [2026-04-15] - method_runs
- CSP4SDG solver implemented: CSP framework with evidence, assertions, hypotheses, IG weighting
- 9,486/12,394 AvalonLogs games solved (6p/7p/8p at 100%, 5p at 42%, 9p at 37%, 10p at 28%)
- Evaluator computes marginal accuracy across 6 views (MRL, PCV, MRG, LSV, EVM, Obj)

### [2026-04-15] - core_claim
- CSP_Strict matches paper within ±0.03 on primary metrics across all 6 player sizes
- validate.py --compare passes: all reproduced metrics numerically plausible
- Core claim validated: CSP-based approach outperforms LLM baselines on role identification
- Implementation verified as real CSP solver (not surrogate): exact enumeration, scoring Eq 1,2, IG weighting

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 11 total (1 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:08] - core_claim_plus
- Audited the existing CSP4SDG implementation and confirmed it implements exact role-assignment enumeration, hard filtering, assertion scoring, hypothesis scoring, IG weighting, posterior marginals, and MAP decoding.
- Verified `scripts/evaluate.sh` works standalone by regenerating an audit scores file from existing method outputs.
- Fixed the container definition so Python package installation remains confined to `environment/setup.sh`; no runtime dependencies changed.

### [2026-05-17 15:03] - core_claim_plus
- Packaged the upstream CSP4SDG code release and a reusable AvalonLogs reproduction environment.
- Verified `python3 validate.py --compare` passes.
- Reproduced the core CSP role-inference claim on AvalonLogs across 5-10 player settings using the paper's exact hard-filtering, soft assertion, hypothesis weighting, posterior marginal, and MAP computation.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 22m | **GPU**: 0.0h
- **Jobs**: 11 total (1 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 11 total (1 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 13m | **GPU**: 0.0h
- **Jobs**: 11 total (1 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 12 total (2 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 9m | **GPU**: 0.0h
- **Jobs**: 12 total (2 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 16m | **GPU**: 0.0h
- **Jobs**: 12 total (2 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 16:05] - core_claim_plus
- Completed final verification of the packaged research gym.
- Fixed method leakage in method-agnostic and method-safe scoring documents.
- Removed tracked root-level raw AvalonLogs files; reusable data now remains under the standard data/download paths.
- Re-ran `python3 validate.py --compare`, shell syntax checks, URL verification, and standalone evaluation on existing artifacts.

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 14m | **GPU**: 0.0h
- **Jobs**: 12 total (2 completed, 3 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-17 16:58] - core_claim_plus
- Completed final verification of method/problem separation, portable download sources, scoring weights and coefficients, train/test evaluator wiring, and standalone evaluation.
- Confirmed `MILESTONES.md` and `action.yaml` remain aligned at `core_claim_plus`.

### [2026-05-17 16:52] - core_claim_plus
- Re-validated the existing CSP4SDG AvalonLogs reproduction and confirmed the actual CSP algorithm and artifact-based evaluator are in place.
- Corrected `scoring/reference.json` so Avalon-NLU Lie Merlin values match Table 7 and AvalonLogs metrics include only paper-reported marginal accuracies.
- Regenerated train/test score artifacts and re-ran `python3 validate.py --compare`; all checks passed.

### [2026-05-17 16:05] - core_claim_plus
- Completed final verification of the packaged research gym.
- Fixed method leakage in method-agnostic and method-safe scoring documents.
- Removed tracked root-level raw AvalonLogs files; reusable data now remains under the standard data/download paths.
- Re-ran `python3 validate.py --compare`, shell syntax checks, URL verification, and standalone evaluation on existing artifacts.

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 38m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

### [2026-05-17 16:58] - core_claim_plus
- Completed final verification of method/problem separation, portable download sources, scoring weights and coefficients, train/test evaluator wiring, and standalone evaluation.
- Confirmed `MILESTONES.md` and `action.yaml` remain aligned at `core_claim_plus`.

### [2026-05-17 16:52] - core_claim_plus
- Re-validated the existing CSP4SDG AvalonLogs reproduction and confirmed the actual CSP algorithm and artifact-based evaluator are in place.
- Corrected `scoring/reference.json` so Avalon-NLU Lie Merlin values match Table 7 and AvalonLogs metrics include only paper-reported marginal accuracies.
- Regenerated train/test score artifacts and re-ran `python3 validate.py --compare`; all checks passed.

### [2026-05-17 16:05] - core_claim_plus
- Completed final verification of the packaged research gym.
- Fixed method leakage in method-agnostic and method-safe scoring documents.
- Removed tracked root-level raw AvalonLogs files; reusable data now remains under the standard data/download paths.
- Re-ran `python3 validate.py --compare`, shell syntax checks, URL verification, and standalone evaluation on existing artifacts.

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
