# Research Direction

## Problem Space

This gym studies hidden-role inference in social deduction games. A scientist should improve how a system turns game histories and viewpoint information into calibrated posterior probabilities over player roles.

## Allowed Directions

Improvements may target:
- better use of public game events,
- better modeling of viewpoint-specific private information,
- more accurate uncertainty calibration,
- more robust inference across player counts,
- more efficient search or approximation as the assignment space grows,
- clearer handling of conflicting or deceptive evidence.

Any approach family is acceptable if it stays within the fixed data, input, output, and evaluation contracts in `scoring/CONSTRAINTS.md`.

## Out of Bounds

The following changes do not count as valid scientific improvements for this gym:
- changing the task from role inference to a different game prediction problem,
- using ground-truth roles or future events as inference-time features,
- evaluating only an easier subset while reporting it as the standard benchmark,
- changing metric definitions, experiment weights, or labels,
- relying on paid APIs or resources unavailable from the reproducible environment.

## Expected Contribution

A successful contribution should improve the weighted evaluation score while preserving broad performance across viewpoints and player counts. It should also document which evidence sources, modeling choices, or inference changes explain the improvement.
