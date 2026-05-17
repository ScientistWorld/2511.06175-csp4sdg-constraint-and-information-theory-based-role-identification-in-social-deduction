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
- [x] `scoring/scores.json` — reproduced AvalonLogs numbers across 5-10 player settings (12,091 games solved)
- [x] Workspace validated via custom comparison script (all structural checks pass)

## Code
- [x] Evaluation code in `eval/`
- [x] Method implementation in `method/`
- [ ] Baseline implementation in `baseline/` (optional — no LLM available for this paper)

## Scripts
- [x] `scripts/evaluate.sh`
- [x] `scripts/reproduce.sh`
- [x] `scripts/download.sh` (idempotent, size comment at top)
- [ ] `scripts/baseline.sh` (optional — no LLM available)
- [x] `scripts/method.sh`
- [x] `scripts/run.sh`

## Environment
- [x] `environment/container.def` + `environment/setup.sh` (CSP is pure Python, runs natively)

## Data
- [x] AvalonLogs dataset downloaded (12,394 converted games from data/avalonlogs_raw/)
- [x] Dataset converted to CSP constraints (data/avalonlogs_constraints/)
- [x] 12,091 games solved across all sizes (data/avalonlogs_solve/) — all 5-9 player games plus 297/600 10-player games
- [x] Remaining hard cases bounded with persistent per-game timeout tracking

## Milestones
- [x] `method_runs` — CSP solver executes end-to-end without errors
- [x] `core_claim` — minimum experiment supports central claim (6-player results match paper)
- [x] `core_claim_plus` — all 6 player sizes evaluated
- [ ] `secondary_claims` — Avalon-NLU/Mafia not reproducible without LLM API
- [ ] `majority`
- [ ] `near_complete`
- [ ] `full`
