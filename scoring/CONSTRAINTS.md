# Scientist Constraints

## Model
The scientist must use the provided CSP4SDG solver as the base method. The solver
must implement the four-constraint framework (evidence, phenomenon, assertions, hypotheses)
with the scoring function S(a) = (prod_{c in A} w_A) * (1 + sum_{h in H} w_H(h)).
The role schema (player counts, good/evil partitions) must match the game's rules.
No external models or neural networks are allowed in the constraint reasoning pipeline.

## Data
The scientist must use the provided AvalonLogs dataset (data/avalonlogs_raw/)
which contains ~12,400 game records. The preprocessed constraints
(data/avalonlogs_constraints/) are derived programmatically from game events
(votes, quests, proposals) — no LLM annotation needed. No external social
deduction game datasets may be added to the evaluation.

## Evaluation Protocol
The scientist must evaluate using the provided eval/evaluator.py script which
computes marginal accuracy and MAP accuracy. Results must be averaged over all
games and all quests within each game, then averaged across games. No cherry-picking
of specific games or quests.

## Scoring
The scientist's scores go in scoring/scores.json. Results must be reported for
the same experiments as reference.json. A future agent must be able to run
`python validate.py --compare` to see a side-by-side comparison.

## Compliance Checklist
- [ ] Using the provided CSP4SDG solver, not a replacement algorithm
- [ ] Using the AvalonLogs dataset, not a different SDG dataset
- [ ] No neural network or LLM in the constraint reasoning path
- [ ] Results averaged over all games and quests in the evaluation
- [ ] scores.json follows the same experiment/metric structure as reference.json
