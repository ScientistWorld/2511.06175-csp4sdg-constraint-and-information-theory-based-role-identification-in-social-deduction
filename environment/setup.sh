#!/bin/bash
# Install Python packages into the container overlay.
#
# CSP4SDG is a pure-Python constraint-satisfaction solver.
# Only the Python standard library is used — no external packages needed.
#
# This script runs inside the Apptainer overlay on compute nodes.
# Use uv pip install --system for speed (uv is pre-installed in the base image).

set -e

echo "CSP4SDG environment setup complete (no external packages needed — pure Python)."
