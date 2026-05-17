# Scientist Constraints

This file defines what a scientist must hold fixed when trying to improve on the
CSP4SDG results, so that improvement requires genuine methodology.

## Model

The scientist must use the provided CSP4SDG solver (`method/sdg_framework.py`) as
the base reasoning engine. The solver must implement the four-constraint framework:
- **Hard constraints**: evidence (quest failures → evil agents on team) and
  phenomenon (role schema validity)
- **Soft constraints**: assertions (multiplicative, high weight) and hypotheses
  (additive, IG-computed weight)

The scoring function S(a) = (prod_{c in A} w_A) * (1 + sum_{h in H} w_H(h)) must
be preserved. The role schema (player counts, good/evil partitions) must match
Avalon's game rules. No neural networks or LLMs are permitted in the reasoning pipeline.

## Data

The scientist must use the AvalonLogs dataset downloaded by `scripts/download.sh`
to `data/downloads/avalonlogs_raw/` and converted to `data/avalonlogs_constraints/`.
The CSP constraint conversion (`data/convert_avalonlogs.py`) derives constraints
programmatically from game events (quest failures, votes, team proposals).
No LLM annotation is used. No external social deduction game datasets may be
substituted for the evaluation.

**Player count filtering:** The reproduced experiments use 6-player and 9-player
games. A scientist may evaluate on 5-10 player games, but results must be reported
separately by player count to match the experiment structure.

## Evaluation Protocol

The scientist must use `eval/evaluator.py` which computes marginal accuracy
(average probability assigned to true roles) and MAP accuracy (fraction of
players with exactly correct role assignments). Results must be averaged over
all games and all quests within each game, then aggregated across games by
player count. No cherry-picking of specific games or quests.

## Scoring Format

Results go in `scoring/scores.json`. Experiment names must match those in
`scoring/reference.json`: `avalonlogs_6player`, `avalonlogs_9player`.
Method names must match: `CSP_Strict`, `CSP_HypIG`.
Metric names must match: `{View}_marginal` (Obj, MRL, PCV, MRG, EVM).

**Run comparison:** `python validate.py --compare`

## Out of Bounds

- Replacing the CSP solver with a neural network or LLM-based role classifier
- Using external LLM APIs for constraint extraction or reasoning (must be self-contained)
- Training or fine-tuning on game data (the method is train-free by design)
- Reporting results on a different dataset without clearly labeling the deviation

## Compliance Checklist

- [x] Using the CSP4SDG solver from `method/sdg_framework.py`
- [x] Using the AvalonLogs dataset from `data/downloads/avalonlogs_raw/`
- [x] No neural network or LLM in the constraint reasoning path
- [x] No training or learning from game data
- [x] Results averaged over all games and quests in the evaluation set
- [x] scores.json uses experiment names `avalonlogs_6player`, `avalonlogs_9player`
- [x] scores.json uses method names `CSP_Strict`, `CSP_HypIG`
- [x] `python validate.py` passes without errors
