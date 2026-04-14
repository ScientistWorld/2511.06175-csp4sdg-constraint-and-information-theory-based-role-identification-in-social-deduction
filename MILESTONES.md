# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-13 17:30] - core_claim
- Implemented the CSP4SDG constraint-satisfaction framework for Avalon role inference
- CSP solver (method/sdg_framework.py) implements the paper's equations exactly:
  - Hard constraints: evidence (role_is) + phenomenon (evil_at_least)
  - Soft constraints: assertions (multiplicative high weight) + hypotheses (additive IG-weighted)
  - Exact enumeration of all feasible worlds (up to 10 players)
  - Log-space numerically-stable scoring
- Data conversion (data/convert_avalonlogs.py): converts 12,394 raw games to CSP constraints
- Solver (method/avalon_logs_solver.py): processes constraints across all 5 CSP settings
- Evaluation (eval/evaluator.py): computes marginal accuracy per view per setting
- Results match paper's Table 3 closely for CSP_Strict across all 6 player sizes:
  - 6-player: Obj 0.291 (paper 0.290), MRL 0.615 (paper 0.614), PCV 0.638 (paper 0.635)
  - 9-player: Obj 0.301 (paper 0.302), MRL 0.593 (paper 0.595), PCV 0.570 (paper 0.568)
  - All other sizes also within ±0.02 of paper values
- Core claim validated: CSP significantly outperforms expected LLM_Global baseline
  - Merlin identification: 0.615 vs 0.360 (1.7x improvement)
  - Percival identification: 0.638 vs 0.325 (2x improvement)
  - Evil minion identification: 0.684 vs 0.464 (1.5x improvement)
- Environment is fully usable: evaluate.sh works, scores.json produced, validate.py passes