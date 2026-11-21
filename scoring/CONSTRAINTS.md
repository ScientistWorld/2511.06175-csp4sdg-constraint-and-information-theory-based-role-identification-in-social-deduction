# Scientist Constraints

These keep improvements about better hidden-role inference rather than a
changed benchmark.

## Data

- Inference may use only what an instance contains: seat labels, the declared
  role composition, the public history up to the cut (proposals, votes, quest
  teams, fail counts) and the viewpoint's private information.
- The visible games in `data/avalonlogs_raw/` (with their roles) may be used to
  fit or tune anything. Nothing else labelled may be used: in particular, no
  copy of the public AvalonLogs corpus beyond the visible games, and no lookup
  of an instance's game in any external source.
- Never read, decode or modify anything under `eval/` from the method.

## Interface

- The method is whatever `scripts/predict.sh <input_dir> <output_dir>` runs. The
  evaluators call it on instances they build; they never retrain anything.
- Predictions must satisfy the validity rules in `briefing/evaluation.md`
  (normalised distributions over the declared roles with consistent role totals,
  and a complete assignment with the declared counts) for every instance.
  Otherwise the method scores the worst value everywhere.
- Each instance must be predicted on its own information. Do not pool
  information across instances.

## Evaluation

Do not edit `eval/`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`,
or `scoring/reference.json` (metrics, coefficients, weights, paper numbers).
Report results per player count and viewpoint.

## Resources

Compute nodes have no internet. Paid APIs and private services are out of
bounds. Learned components must be reproducible from the workspace.
