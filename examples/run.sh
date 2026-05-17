#!/bin/bash
# Example run.sh — update this file before each job submission.
#
# This runs inside the compute container with:
#   - Your workspace mounted in the container
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Example: train a model
python method/train.py --epochs 10 --lr 0.001

# Example: evaluate
./evaluate.sh checkpoints/best.pt
