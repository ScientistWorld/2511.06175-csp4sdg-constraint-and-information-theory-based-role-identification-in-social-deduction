# Research Direction

## Problem space

Hidden-role inference in social deduction games: turn a public game history and
a viewpoint's private information into calibrated posteriors over every
player's role.

## Allowed directions

- Better use of public events (proposals, votes, quest results) as evidence.
- Fuller and more principled use of each viewpoint's private information.
- Better weighting or modelling of soft evidence, including models fitted on the
  visible training games.
- Calibration of the posterior (the ranked metric is a proper scoring rule).
- More robust behaviour across player counts and compositions.
- Faster or approximate inference, as long as predictions stay valid.

Any approach family is fine within `scoring/CONSTRAINTS.md`.

## Out of bounds

- Using roles or future events of the instance being predicted, or looking an
  instance up in the public corpus.
- Reading or changing anything in `eval/`, or the ranked metrics, weights and
  labels.
- Pooling information across instances.
- Paid APIs or resources the reproducible environment does not have.

## Expected contribution

Lower experiment-weighted Brier on the hidden test, across viewpoints and player
counts, with a clear account of which evidence or modelling change explains the
gain. Report paired comparisons against the reference on identical instances.
