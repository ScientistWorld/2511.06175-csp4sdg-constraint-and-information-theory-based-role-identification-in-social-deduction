# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-06] - method_runs
- Implemented the CSP4SDG solver based on the paper's code (method/sdg_framework.py, method/avalon_logs_solver.py)
- CSP solver runs end-to-end on AvalonLogs data without errors
- Data preprocessing (convert_avalonlogs.py) successfully converts raw game logs to CSP constraints
- Optimized solver processes 6-8 player games in ~1-10s per game (9-10 player games are slow due to combinatorial explosion)
- AvalonLogs dataset: 12,402 game files, converted to constraints
- Evaluation code computes marginal accuracy and MAP accuracy per game, aggregated across games

### [2026-04-06] - none
- Read the paper and identified key components: CSP framework, four constraint types, IG weighting
- Cloned CSP4SDG GitHub repo for reference implementation
- Downloaded AvalonLogs dataset (12,402 games) from GitHub
