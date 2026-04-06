# Research Direction

## Research Problem
This paper addresses hidden-role inference in social deduction games. Given incomplete,
noisy, and potentially deceptive information from game events and dialogue, the goal
is to infer the most likely role assignment for each player. The core challenge is that
the combinatorial space of role assignments grows factorially with player count, and
players deliberately deceive each other.

## Core Contribution
The paper's key contribution is CSP4SDG: a constraint-satisfaction framework that
decomposes game information into four linguistically-agnostic constraint types and uses
information-gain-weighted soft constraints to compute calibrated role posteriors. The
scientist should work within this constraint-reasoning paradigm — improving how
constraints are extracted, weighted, or solved.

## Approach Scope
The scientist may explore improvements in:
- **Constraint extraction**: better extraction of constraints from game events
- **Constraint weighting**: improved information-gain or alternative weighting schemes
- **Inference algorithms**: faster or more accurate CSP solving
- **Multi-game reasoning**: aggregating evidence across multiple games or rounds
- **Perspective modeling**: better modeling of what each role perspective knows

The scientist may NOT use:
- Neural networks or LLMs as the primary reasoning engine
- External game datasets beyond the provided AvalonLogs corpus
- Ensemble methods combining fundamentally different reasoning paradigms
- Training or learning from game data (the method is train-free by design)

## Out of Bounds
- Replacing the CSP solver with a neural network or transformer-based role classifier.
  The paper's thesis is that structured combinatorial reasoning is essential for SDG
  role inference — switching to end-to-end learning sidesteps this thesis entirely.
- Using external LLM APIs to extract constraints or reason about roles. The method
  must be self-contained and runnable without internet access.
- Scaling up to more players or different SDG variants without demonstrating that
  the improvement is due to methodological innovation, not just more data.
