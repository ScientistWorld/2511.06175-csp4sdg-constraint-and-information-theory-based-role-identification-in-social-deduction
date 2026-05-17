# Scientist Constraints

These constraints define what must stay fixed so improvements reflect better hidden-role inference rather than a changed benchmark.

## Data

Use the AvalonLogs data downloaded by `scripts/download.sh` and the tracked conversion utilities under `data/`. Do not substitute a different dataset for the reported AvalonLogs experiments. Additional datasets may be explored only as clearly labeled extra experiments.

Ground-truth roles may be used only for evaluation, never as an inference-time input.

## Inputs

Methods may condition on:
- player identities within a game,
- public game events,
- declared role composition,
- viewpoint-specific private information allowed by the game rules.

Methods may not condition on future events for an earlier evaluated state, hidden roles outside the allowed viewpoint, or external annotations unavailable to all competitors.

## Outputs

Every method must produce:
- posterior probabilities over possible roles for each player,
- one best full role assignment per evaluated viewpoint,
- artifacts readable by `eval/evaluator.py`.

Predicted assignments must respect the role composition for the game being evaluated.

## Evaluation

Use the provided evaluation scripts without editing metrics, experiment weights, or ground-truth labels:

```bash
bash scripts/evaluate.sh
python validate.py --compare
```

Results must be reported separately by player count and viewpoint. Do not cherry-pick games, player counts, or viewpoints.

## Resource and Reproducibility Limits

The benchmark must run without internet access on compute nodes. Paid APIs and private services are out of bounds. If a method uses learned components, their training data, checkpoints, and inference procedure must be reproducible from files available in the workspace or downloaded by `scripts/download.sh`.
