#!/bin/bash
# Install Python packages into the container overlay.
#
# CSP4SDG is a pure-Python constraint-satisfaction solver.
# Only standard library is used — no external packages needed.

set -e

# No external Python packages required.
# The method uses only Python's built-in libraries:
#   itertools, math, collections, json, random, pathlib
# The eval module also uses only standard library.

echo "CSP4SDG environment setup complete (no external packages needed)."
