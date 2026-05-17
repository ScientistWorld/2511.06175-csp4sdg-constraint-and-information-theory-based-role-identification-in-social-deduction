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
