# Experiment Overview

This file describes the experiments that appear in `scoring/scores.json`. It is intentionally method-agnostic: any system that produces the required posterior and MAP outputs can be evaluated by the same scripts.

The paper reports AvalonLogs as 12,699 games. This reproduction converted 12,394 usable raw logs from the public repository and produced scored artifacts for 12,091 games.

## avalonlogs_6player

Primary reproduced experiment. It evaluates hidden-role inference on 3,176 solved 6-player Avalon games. This setting is important because it is large enough to include special-role and team-side uncertainty while still having broad dataset coverage.

Primary metric: `Obj_marginal`.

Supporting metrics: viewpoint-specific marginal and MAP accuracy for Merlin, Percival, Morgana, and non-special evil perspectives.

## avalonlogs_9player

Secondary high-weight experiment. It evaluates 843 solved 9-player games and tests whether a method remains useful as the assignment space and role composition become larger.

Primary metric: `Obj_marginal`.

Supporting metrics: the same viewpoint-specific metrics as the 6-player experiment.

## avalonlogs_5player

Small-game experiment with 3,359 solved games. It checks that a method handles simpler role compositions and high-coverage data without special casing.

## avalonlogs_7player

Intermediate-complexity experiment with 2,735 solved games. It provides a bridge between the small and large game-size settings.

## avalonlogs_8player

Larger intermediate experiment with 1,681 solved games. It tests robustness as the number of possible full assignments increases.

## avalonlogs_10player

Largest reproduced setting, with 297 solved games. Coverage is partial because the role-assignment space is largest here, but the experiment is useful as a stress test for scaling behavior.

## Scoring Emphasis

The highest weights in `scoring/reference.json` are assigned to the 6-player and 9-player settings. When only the experiments present in `scores.json` are considered, those two settings dominate the gym score, while the remaining player counts provide breadth and regression checks.
