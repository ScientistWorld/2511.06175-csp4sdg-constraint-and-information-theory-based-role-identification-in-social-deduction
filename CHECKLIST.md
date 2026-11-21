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
- [x] `scoring/scores.json` / `scores_train.json` / `scores_test.json` — reference scores (train slice / train / hidden test)
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
- [x] AvalonLogs visible games in data/avalonlogs_raw/ (6,205 files; the 6,197 hidden test games live only in eval/test/)
- [x] Method runs on evaluation instances through scripts/predict.sh (no cached outputs)

## Milestones
- [x] `method_runs` — CSP solver executes end-to-end without errors
- [x] `core_claim` — minimum experiment supports central claim (6-player results match paper)
- [x] `core_claim_plus` — all 6 player sizes evaluated
- [ ] `secondary_claims` — Avalon-NLU/Mafia not reproducible without LLM API
- [ ] `majority`
- [ ] `near_complete`
- [ ] `full`
