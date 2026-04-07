#!/bin/bash
# Install Python packages into the container overlay.
#
# CSP4SDG is a pure-Python constraint-satisfaction solver.
# Only standard library is used — no external packages needed.

set -e

# Install uv for future package needs (pre-installed on many base images)
if command -v uv &>/dev/null; then
    echo "uv already available"
elif command -v pip3 &>/dev/null; then
    pip3 install uv --quiet 2>/dev/null || true
fi

echo "CSP4SDG environment setup complete (no external packages needed)."
