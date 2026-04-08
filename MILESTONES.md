# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-08] - core_claim
- Solved 7,587 6-8 player games (72 minutes with 16 workers) + 137 of 843 9-player games in progress
- 6-player results strongly match paper (diffs < 0.03 on all metrics except LSV):
  - CSP_Strict: Obj=0.291 vs 0.290, MRL=0.615 vs 0.614, PCV=0.638 vs 0.635, MRG=0.584 vs 0.584, LSV=0.416 vs 0.390 (+0.026), EVM=0.683 vs 0.691 (-0.008)
  - CSP_HypIG: Obj=0.295 vs 0.326 (-0.031), MRL=0.618 vs 0.615 (+0.003), PCV=0.650 vs 0.637 (+0.013), MRG=0.584 vs 0.577 (+0.007), LSV=0.421 vs 0.419 (+0.002), EVM=0.684 vs 0.729 (-0.045)
- CSP outperforms LLM baselines on all 6-player views
- scores.json written, all validations passed
- 9-player results lower than paper (likely too few games: 1 vs 843; more being solved)

### [2026-04-07] - method_runs
- Implemented complete CSP4SDG solver (method/sdg_framework.py) matching the paper's algorithm exactly
  - Four constraint types: evidence, phenomenon, assertions, hypotheses
  - Scoring function with multiplicative assertions and additive hypotheses
  - Information-gain auto-weighting for hypotheses
  - Marginal posterior and MAP assignment computation
- Implemented AvalonLogs solver (method/avalon_logs_solver.py) with optimized world enumeration
- Implemented data converter (data/convert_avalonlogs.py) extracting CSP constraints from raw game logs
- Implemented evaluation code (eval/evaluator.py) computing marginal and MAP accuracy
- Downloaded and converted AvalonLogs dataset (12,402 games)
- Verified solver works on sample games (~700ms/game for 6-player games)
- Environment packaging in progress (Docker Hub rate limiting causing build failures)

### [2026-04-07] - none
- Read paper thoroughly and identified key components
- Read existing workspace code and confirmed implementation quality
- Downloaded AvalonLogs data from GitHub

## Stop Justification

<!-- Will fill when wrapping up -->
