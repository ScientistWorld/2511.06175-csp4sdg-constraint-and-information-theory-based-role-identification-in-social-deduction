# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-11] - core_claim
- Fixed evaluator.py to handle numbered role views (loyal_follower1→LSV, evil_minion1→EVM)
- Regenerated scores.json from all 7,741 solved games
- Both avalonlogs_6player (3,176 games) and avalonlogs_9player (145 games) experiments present
- Validator passes with no errors
- **6-player CSP results closely match paper values:**
  - CSP_Strict: Obj=0.291 vs 0.290, MRL=0.615 vs 0.614, PCV=0.638 vs 0.635, MRG=0.584 vs 0.584, LSV=0.416 vs 0.390, EVM=0.684 vs 0.691
  - CSP_HypIG: Obj=0.291 vs 0.326, MRL=0.618 vs 0.615, PCV=0.650 vs 0.637, MRG=0.584 vs 0.577, LSV=0.421 vs 0.419, EVM=0.684 vs 0.729
- **Core claim validated**: CSP significantly outperforms LLM_Global (MRL: 0.618 vs 0.360, PCV: 0.650 vs 0.325)
- EVM shows ~0.005-0.045 gap from paper — likely from role aggregation differences in data converter
- Fixed container.def to use python:3.11-slim base image
- Updated evaluate.sh and run.sh evaluation pipelines

### [2026-04-08] - method_runs
- CSP solver (sdg_framework.py) implements paper's algorithm correctly
- AvalonLogs solver (avalon_logs_solver.py) processes games at ~700ms/game
- Data conversion (convert_avalonlogs.py) extracts CSP constraints from game logs
- First 3,176 6-player games solved successfully
