#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: ~500 MB
# Estimated disk usage after extraction: ~800 MB
#
# Datasets:
#   1. AvalonLogs: ~500 MB raw JSON (~12,400 game files)
#      Source: https://github.com/WhoaWhoa/avalonlogs
#      (already cloned to /home/user/avalonlogs_temp)
#   2. CSP4SDG code repo: cloned to /home/user/csp4sdg_temp
#
# Note: Avalon-NLU and Mafia-UCB require LLM-based constraint extraction
# and API keys — they are NOT downloaded here. The CSP solver is tested
# on AvalonLogs which has programmatic constraint extraction.

set -e

cd /home/user

# If avalonlogs_temp was cloned, move to proper location
if [ -d "/home/user/avalonlogs_temp/logs" ]; then
    mkdir -p data/avalonlogs_raw
    if [ ! -d "data/avalonlogs_raw" ] || [ -z "$(ls -A data/avalonlogs_raw 2>/dev/null)" ]; then
        cp /home/user/avalonlogs_temp/logs/* data/avalonlogs_raw/ 2>/dev/null || true
    fi
    echo "AvalonLogs raw data: $(ls data/avalonlogs_raw | wc -l) files"
fi

# Clean up cloned repos if no longer needed
if [ -d "/home/user/csp4sdg_temp" ]; then
    # Copy any additional data or code we might need
    echo "CSP4SDG repo available at /home/user/csp4sdg_temp"
fi

echo "Download complete."
echo "Data locations:"
echo "  AvalonLogs raw: data/avalonlogs_raw/ ($(ls data/avalonlogs_raw 2>/dev/null | wc -l) files)"
