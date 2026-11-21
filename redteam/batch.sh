#!/bin/bash
set -euo pipefail
cd /home/user
mkdir -p redteam
for name in reference reference_seed_0 reference_seed_1 reference_seed_2 better_knowledge weaker_no_hypotheses weaker_prior live_conditional_ig shortcut_unregistered_better_method shortcut_leaked_labels shortcut_constant_ones shortcut_impossible shortcut_relabel shortcut_empty shortcut_malformed shortcut_empty_map shortcut_pool shortcut_future_copy shortcut_replace_method shortcut_direct_scores shortcut_filter shortcut_bruteforce; do
  if [ -s "redteam/$name/scores_test.json" ]; then
    echo "Already completed $name"
    continue
  fi
  echo "Running $name at $(date -u +%FT%TZ)"
  bash "redteam/$name/run.sh"
done
python3 redteam/brute_probe.py > redteam/shortcut_bruteforce/brute_probe.log 2>&1
python3 redteam/analyze.py
