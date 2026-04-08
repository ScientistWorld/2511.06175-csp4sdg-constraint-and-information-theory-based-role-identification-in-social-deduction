# Reproduction Checklist

Check off items as you complete them. Order doesn't matter — work however makes sense for this paper.

## Briefing
- [x] `briefing/problem.md` (method-agnostic)
- [x] `briefing/evaluation.md` (method-agnostic)
- [x] `briefing/method.md`
- [x] `briefing/overview.md`

## Scoring
- [x] `scoring/reference.json` — paper's reported numbers
- [x] `scoring/EXPERIMENTS.md` — high-level purpose of each experiment
- [x] `scoring/TARGETS.md` — primary, constraint, and ablation targets
- [x] `scoring/CONSTRAINTS.md` — what a scientist must hold fixed
- [x] `scoring/DIRECTION.md` — research direction scope for scientist
- [x] `scoring/scores.json` — reproduced numbers (6-player done, 9-player ~10% done)
- [x] Workspace validated via `python validate.py`

## Code
- [x] Evaluation code in `eval/`
- [x] Method implementation in `method/`
- [ ] Baseline implementation in `baseline/` (optional — AvalonLogs has no LLM baseline)

## Scripts
- [x] `scripts/evaluate.sh`
- [ ] `scripts/reproduce.sh`
- [x] `scripts/download.sh` (idempotent, size comment at top)
- [ ] `scripts/baseline.sh` (optional)
- [x] `scripts/method.sh`
- [x] `scripts/run.sh`

## Environment
- [x] `environment/container.def` + `environment/setup.sh` (CSP is pure Python, runs natively)

## Data
- [x] AvalonLogs dataset downloaded (12,402 games in data/avalonlogs_raw/)
- [x] Dataset converted to CSP constraints (data/avalonlogs_constraints/)
- [x] 7,587 6-8 player games solved (data/avalonlogs_solve/)
- [ ] 843 9-player games solved (in progress, ~137 done)

## Milestones
- [x] `method_runs` — CSP solver executes end-to-end without errors
- [x] `core_claim` — minimum experiment supports central claim (6-player results match paper)
- [ ] `core_claim_plus` — additional settings
- [ ] `secondary_claims`
- [ ] `majority`
- [ ] `near_complete`
- [ ] `full`
