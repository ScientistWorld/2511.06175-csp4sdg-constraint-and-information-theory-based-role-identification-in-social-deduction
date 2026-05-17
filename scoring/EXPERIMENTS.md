# Experiment Overview

This file describes what each experiment in `scores.json` is trying to establish.
The paper reports AvalonLogs as 12,699 games. This reproduction converted 12,394
usable raw logs from the public repository and solved 12,091 of them.

## avalonlogs_6player (weight: 0.2083 — highest weight, primary result)
Evaluates CSP-based role inference on 6-player Avalon games (3,176 games).
6-player Avalon has 2 good special roles (Merlin + Percival) against 2 evil (Morgana + 1 Minion).

This is the primary experiment establishing the core claim: CSP with constraint-based
inference can accurately identify hidden roles. Two configurations are evaluated:
- **CSP_Strict**: Hard constraints only (evidence + phenomenon)
- **CSP_HypIG**: Hard constraints + hypotheses with Information-Gain auto-weighting

Results closely match the paper's Table 3 (AvalonLogs-6p column). CSP_Strict reproduces
within ±0.01 on all views. CSP_HypIG in our implementation produces results closer to
Strict (the IG weighting does not yield the paper's large Obj gain of +0.036).

## avalonlogs_9player (weight: 0.1667 — second highest)
Evaluates CSP on 9-player games (843 solved). Tests scalability to larger
combinatorial space (3 evil vs 6 good). CSP_Strict closely matches the paper (±0.01).

## avalonlogs_5player (weight: 0.0417)
5-player games (3,359 solved). Entry-level setup with fewer players and simpler role
structures. Results match paper closely for CSP_Strict.

## avalonlogs_7player (weight: 0.0417)
7-player games (2,735 solved). Intermediate complexity. Results match paper closely.

## avalonlogs_8player (weight: 0.0417)
8-player games (1,681 solved). Higher combinatorial space. Results match paper closely.

## avalonlogs_10player (weight: 0.0417)
10-player games (297 solved, partial). Largest combinatorial space.
Results match paper closely for both Strict and HypIG.

## Key Finding
CSP_Strict results consistently match the paper across all player sizes (within ±0.02).
The CSP framework is confirmed to work for hidden-role inference. The HypIG improvement
over Strict is smaller in our implementation than in the paper, likely due to differences
in how hypotheses are extracted from AvalonLogs vote/team data vs the paper's
LLM-based extraction on dialogue datasets.
