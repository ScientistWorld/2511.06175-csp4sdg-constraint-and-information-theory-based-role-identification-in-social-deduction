# Experiment Overview

All experiments measure hidden-role inference on real AvalonLogs games (public
game logs, no dialogue), one experiment per player count. They are
method-agnostic: anything that turns an instance (game prefix + viewpoint) into
per-player role distributions and a complete assignment through
`scripts/predict.sh` is scored the same way. The protocol is in
`briefing/evaluation.md`.

Each experiment has twelve metrics: `{view}_brier` (ranked, lower is better)
and `{view}_marginal` (the paper's reported quantity, coefficient 0) for the
views `Obj`, `MRL`, `PCV`, `MRG`, `LSV`, `EVM`. The hidden test uses 6,197
held-out games, one instance each; the train slice uses the 6,196 visible games
the same way.

## avalonlogs_6player (weight 0.35)

1,588 held-out games (~265 per viewpoint). The paper's main-text small-game
setting: two or three evil players among six, with Merlin, Percival and
Morgana in most games.

## avalonlogs_9player (weight 0.25)

421 held-out games (~70 per viewpoint). The paper's main-text large-game
setting: three evil players among nine, a larger assignment space and more
loyal followers.

## avalonlogs_5player (weight 0.10)

1,679 held-out games (~280 per viewpoint). Smallest games; checks that a method
handles simple compositions without special casing.

## avalonlogs_7player (weight 0.10)

1,369 held-out games (~228 per viewpoint). Three evil among seven; the hardest
size for public-information inference.

## avalonlogs_8player (weight 0.10)

840 held-out games (~140 per viewpoint).

## avalonlogs_10player (weight 0.10)

300 held-out games (~50 per viewpoint). Four evil among ten, up to 151,200
complete assignments; the noisiest cell sizes.

## Scoring emphasis

6p and 9p carry the most weight, following the paper's main-text table; the
other sizes keep a method from trading one game size for another. Within an
experiment every viewpoint counts equally.
