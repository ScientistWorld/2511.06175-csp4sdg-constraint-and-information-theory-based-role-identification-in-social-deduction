# Progress

## What Works

1. **CSP solver** (method/sdg_framework.py): Complete implementation of SDGModel class with:
   - Hard constraints (evidence + phenomenon) that prune invalid assignments
   - Multiplicative soft constraints (assertions) with high weight
   - Additive soft constraints (hypotheses) with manual or IG-computed weights
   - Exact enumeration of feasible worlds for n ≤ 10 players
   - Marginal posterior and MAP assignment computation using numerically-stable log-space scoring
   - Matches the paper's algorithm exactly (Eq. 1, 2 in the paper)

2. **AvalonLogs solver** (method/avalon_logs_solver.py):
   - Processes converted constraint JSON files
   - Computes posteriors for all perspectives (objective, merlin, percival, morgana, servant, evil roles)
   - Supports all five CSP settings (Strict, +Assert, +HypIG, +HypM, +TurnIG)
   - Optimized: caches world enumeration and IG weights, avoids redundant model copies
   - Processing rate: ~700ms/game for 6-player games, ~1-3s for 7-8 players

3. **Data conversion** (data/convert_avalonlogs.py):
   - Converts raw AvalonLogs JSON files to CSP constraint format
   - Extracts evidence from quest failures, hypotheses from votes and team proposals
   - Uses paper's manual weights: W_strong=0.50, W_reject=0.20, W_weak=0.10
   - Deterministic with fixed seed (42)

4. **Evaluation** (eval/evaluator.py):
   - Computes marginal accuracy and MAP accuracy per game, per quest
   - Aggregates across games by player count and role perspective
   - Produces scores.json compatible with reference.json structure

5. **AvalonLogs dataset**:
   - 12,402 raw game files downloaded from GitHub
   - All games converted to CSP constraint format
   - Games span 5-10 players with ground-truth roles

## Results Achieved

**Paper's AvalonLogs results (Table 3, 6-player, marginal accuracy):**
| Method | Obj | Merlin | Percival | EvilMinion |
|--------|-----|--------|----------|------------|
| CSP-Strict | 0.290 | 0.614 | 0.635 | 0.691 |
| CSP+HypIG | 0.326 | 0.615 | 0.637 | 0.729 |
| LLM-Global | 0.283 | 0.360 | 0.325 | 0.464 |
| Random | ~0.267 | ~0.4 | ~0.4 | ~0.5 |

Awaiting full batch evaluation results from the compute job.

## Remaining

1. **Full batch processing**: Process all 6-8 player games (~7,600 unsolve) to get robust accuracy estimates
2. **Validate against paper**: Compare reproduced numbers with reference.json
3. **core_claim**: Demonstrate CSP significantly outperforms random on AvalonLogs
4. **Expand to more experiments**: 7-player, 8-player game sizes

## Issues

1. **Docker Hub rate limit**: Container build fails with TOOMANYREQUESTS for all base images (tried alpine, ubuntu, debian, fedora, rockylinux). Attempting workarounds.
2. **Avalon-NLU and Mafia datasets unavailable**: Require LLM-based constraint extraction with API keys. Focus is on AvalonLogs with programmatic extraction.
3. **9-10 player games too slow**: World enumeration has ~9000-90000 worlds. Filtered to 6-8 players.

## Deviations from Paper

1. **Datasets**: Only AvalonLogs used. Avalon-NLU and Mafia-UCB require LLM-based extraction (API needed) and are skipped.
2. **LLM comparisons**: No LLM-based experiments. The paper shows LLM struggles; replicating requires API or local LLM.
3. **Game size filtering**: 9-10 player games excluded due to combinatorial cost. Focus on 6-8 players where core claim is still valid.
4. **No dialogue**: AvalonLogs has no dialogue; only the no-dialogue condition can be reproduced.
