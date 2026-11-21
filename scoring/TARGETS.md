# Evaluation Targets

The target is better hidden-role posteriors on held-out AvalonLogs game
prefixes, under the fixed protocol in `briefing/evaluation.md`.

## Primary targets

Lower `*_brier` (all six viewpoints) on:
- `avalonlogs_6player` (weight 0.35)
- `avalonlogs_9player` (weight 0.25)

## Breadth targets

Lower or equal `*_brier` on `avalonlogs_5player`, `avalonlogs_7player`,
`avalonlogs_8player`, `avalonlogs_10player` (0.10 each). Gains on the public
views (`Obj`, `LSV`) and on the informed views (`MRL`, `PCV`, `MRG`, `EVM`)
both count; a method should not buy one with the other.

## Reported, not ranked

`*_marginal` (mean probability on the true role) is the paper's AvalonLogs
quantity and is reported so results can be compared with the paper. It has
coefficient 0: it is linear in the prediction, so it rewards overconfident
posteriors.

## Output requirement

`scripts/predict.sh <input_dir> <output_dir>` must write a valid prediction for
every instance and every method name it emits (see the validity rules in
`briefing/evaluation.md`); otherwise that method gets the worst value of every
metric. Develop with:

```bash
bash scripts/evaluate_train.sh            # visible games, writes scoring/scores_train.json
bash scripts/evaluate_train.sh --limit-per-size 100   # quick check
python validate.py
```
