# Evaluation Targets

This file defines what future scientist agents should optimize. The target is hidden-role inference from AvalonLogs game histories under the fixed evaluation protocol.

## Primary Targets

Improve `Obj_marginal` on:
- `avalonlogs_6player`
- `avalonlogs_9player`

These two experiments carry the largest weights among the reproduced scores. They should remain the main focus for method improvements.

## Secondary Targets

Improve or maintain viewpoint-specific metrics across all reproduced player counts:
- `MRL_marginal`
- `PCV_marginal`
- `MRG_marginal`
- `EVM_marginal`

Strong results should not come from improving only the objective/public view while degrading role-specific viewpoints.

## Breadth Targets

The smaller-weight experiments (`avalonlogs_5player`, `avalonlogs_7player`, `avalonlogs_8player`, and `avalonlogs_10player`) test robustness across game sizes. A useful improvement should either improve multiple player counts or clearly document which setting it targets.

## Output Requirement

New methods should write artifacts in the same schema consumed by `eval/evaluator.py`, then run:

```bash
bash scripts/evaluate.sh
python validate.py --compare
```

The gym score is based on the experiments present in `scoring/scores.json`; experiment weights from `scoring/reference.json` are renormalized over that reproduced subset.
