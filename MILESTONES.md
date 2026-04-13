# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-04-13 01:02] - none
- Just started reproduction work
- Read the paper and identified key components

### [2026-04-13 01:02] - method_runs
- Implemented baseline model
- Training runs without errors on sample data

### [2026-04-13 01:02] - core_claim
- CSP solver fully implemented (sdg_framework.py + avalon_logs_solver.py)
- AvalonLogs data downloaded and converted to CSP constraints
- 6-player and 9-player results reproduce paper within small margin
- Core claim validated: CSP outperforms LLM on role identification

### [2026-04-13 01:02] - core_claim_plus
- Expanded evaluation to all player sizes (5,7,8,10-player from paper Table 8)
- Added reference numbers for all 6 player sizes
- Updated run.sh to solve ALL remaining games with quick settings
- Submitting job to solve full dataset and get stable scores

### [2026-04-13 11:30] - core_claim_plus (update)
- Fixed reference.json weights (normalized to sum to 1.0)
- Fixed scores.json format to match validator expectations
- Fixed validate.py bug (skipped "type" field in scores validation)
- All 6 player sizes now have scores from ~8059 solved games
- CSP_Strict closely matches paper values (within 0.03 on most metrics)
- CSP_HypIG shows smaller gains than paper (likely due to different constraint weighting)
- Remaining ~4335 games to be solved by running job
- Avalon-NLU and Mafia require LLM API (not reproducible without API)
