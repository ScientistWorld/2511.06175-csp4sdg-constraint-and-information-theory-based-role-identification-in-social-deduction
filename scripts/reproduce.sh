#!/bin/bash
# Reproduce the paper's AvalonLogs results end to end:
#   1. make sure the visible AvalonLogs games are present (scripts/download.sh)
#   2. score the role-count prior baseline on the train games (scripts/baseline.sh)
#   3. run CSP4SDG through the train and hidden-test evaluators (scripts/run.sh)
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/download.sh
bash scripts/baseline.sh
bash scripts/run.sh
bash scripts/method.sh
