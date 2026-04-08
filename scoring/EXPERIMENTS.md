# Experiment Overview

This file describes what each experiment in `scores.json` is trying to establish.
The experiments evaluate the CSP4SDG method on the AvalonLogs dataset.

## avalonlogs_6player
Evaluates CSP-based role inference on 6-player Avalon games (3,176 games).
6-player Avalon has 2 good agents (Merlin + Percival) against 2 evil agents (Morgana + 1 Minion).

This establishes the core claim: CSP with constraint-based inference can accurately
identify hidden roles in social deduction games. The primary metric is marginal accuracy
(Obj_marginal) which measures the average probability the CSP assigns to true roles.

Two CSP configurations are evaluated:
- **CSP_Strict**: Hard constraints only (evidence + phenomenon)
- **CSP_HypIG**: Hard constraints + hypotheses with Information-Gain auto-weighting

The experiment tests whether the CSP framework produces meaningful role identification
above random chance, and whether IG-based hypothesis weighting improves results.

## avalonlogs_9player
Evaluates CSP-based role inference on 9-player Avalon games (145 games, partial).
9-player Avalon has 3 evil agents against 6 good agents (including Merlin + Percival).

This tests whether the CSP framework scales to more players where the combinatorial
space of possible assignments is larger. The primary metric is Obj_marginal.
Results are partial (145/843 games) — full convergence requires more compute time.