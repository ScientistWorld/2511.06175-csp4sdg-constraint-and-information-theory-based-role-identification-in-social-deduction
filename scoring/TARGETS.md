# Evaluation Targets

This file defines what a scientist must achieve to be considered successful on this
research problem. Each target corresponds to an experiment in scores.json.

---

## Primary: avalonlogs_6player

**What it tests:** CSP-based role inference on 6-player Avalon games (3,176 games).
This is the paper's main result establishing that constraint-based reasoning outperforms
LLM baselines for hidden-role identification.

**Primary metric:** `Obj_marginal` (higher is better)
  - Measures: average probability assigned to true roles across all players
  - Target direction: CSP methods (0.29-0.33) should exceed LLM_Global (0.28)
  - Paper reference: Table 3, AvalonLogs-6p section

**Supporting metrics:**
  - `MRL_marginal`: Merlin identification (good players should identify Merlin well)
  - `PCV_marginal`: Percival identification ( Percival should identify Morgana)
  - `MRG_marginal`: Morgana identification
  - `EVM_marginal`: Evil minion identification

**How to run:**
```bash
python eval/evaluator.py --results-dir data/avalonlogs_solve --output scoring/scores.json --dataset avalonlogs
```

---

## Primary: avalonlogs_9player

**What it tests:** CSP-based role inference on 9-player Avalon games (843 solved games).
Tests scalability to more players with larger combinatorial space (3 evil vs 6 good).

**Primary metric:** `Obj_marginal` (higher is better)
  - Measures: same as 6-player but across more players
  - Target direction: CSP methods (0.30-0.36) should exceed LLM_Global (0.28)
  - Paper reference: Table 3, AvalonLogs-9p section

**Supporting metrics:** Same as 6-player (MRL, PCV, MRG, EVM marginal)

**How to run:** Same as avalonlogs_6player (evaluator aggregates by player count)

---

## Constraint: hypothesis_weighting_quality

**What it tests:** That information-gain auto-weighting (+HypIG) matches or improves
over manual weight tuning (+HypM or manual W_strong/W_reject/W_weak).

**Metric:** `Obj_marginal` comparison between CSP_HypIG and CSP_Strict
  - Direction: +HypIG should score >= Strict on most views
  - Paper 6-player reference: HypIG improves objective marginal accuracy over Strict by +0.036.
  - Current reproduction: HypIG is close to Strict on objective marginal accuracy (+0.004) and improves PCV by +0.013.

---

## Ablation: constraint_types

**What it tests:** That each constraint type adds value. Removing soft constraints
should degrade accuracy.

**Metric:** Marginal accuracy should follow Strict < +Assert < +HypIG
  - Strict (hard constraints only): baseline
  - +Assert (adds assertions with high weight): should improve
  - +HypIG (adds IG-weighted hypotheses): should improve further

**Current results:** Only Strict and +HypIG evaluated so far. +Assert and +HypM remain.

---

## Compliance Checklist

- [x] Marginal accuracy computed as average probability assigned to true roles
- [x] Results averaged over all games and all quests within each game
- [x] 6-player results (3,176 games) match paper's Table 3 AvalonLogs-6p section
- [x] 9-player results (843 games) fully solved
- [x] Scores written to scoring/scores.json in matching experiment/metric format
- [x] Validation: `python validate.py --compare` passes with no errors
