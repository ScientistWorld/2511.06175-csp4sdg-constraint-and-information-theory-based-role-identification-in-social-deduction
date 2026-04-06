# Experiment Overview

This file describes what each experiment in `scores.json` is trying to establish.
The experiments come from the paper's evaluation on the AvalonLogs dataset, which
records public game events (quests, votes, team proposals) for thousands of Avalon games.

## avalonlogs_6p_strict
Evaluates CSP-based role inference on 6-player Avalon games using only hard constraints
(evidence + phenomenon). This establishes the baseline performance when no soft
constraints (assertions or hypotheses) are used.

## avalonlogs_6p_hypig
Evaluates CSP-based role inference on 6-player Avalon games using hard constraints
plus hypotheses with information-gain auto-weighting. This tests whether
automatically-computed hypothesis weights improve role identification.

## avalonlogs_7p_strict / avalonlogs_7p_hypig
Same as above but for 7-player games. 7-player Avalon introduces a third evil agent,
which the paper notes makes inference harder (see Appendix H of the paper).

## avalonlogs_8p_strict / avalonlogs_8p_hypig
Same as above but for 8-player games. 8-player Avalon adds extra loyal servants
without increasing the evil count, which the paper notes makes inference easier
for certain roles.

## avalonlogs_9p_strict / avalonlogs_9p_hypig
Same as above but for 9-player games. 9-player Avalon has 4 loyal servants plus
Merlin and Percival against 3 evil agents.

## comparison_6p_vs_random
Compares CSP accuracy against a random assignment baseline on 6-player games.
The random baseline assigns roles uniformly at random from feasible assignments.
A good method should substantially outperform random on all role perspectives.

## comparison_8p_vs_random
Same comparison for 8-player games.
