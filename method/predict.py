#!/usr/bin/env python3
"""
Method entry point for the gym interface (called by scripts/predict.sh).

    python3 -m method.predict <input_dir> <output_dir>

Reads <input_dir>/instances.json and writes <output_dir>/predictions.json:

    {"predictions": {instance_id: {method_name: {"posterior": {player: {role: p}},
                                                 "best": {player: role}}}}}

Every method name written here is scored by the evaluators.  The reference
writes the paper's CSP4SDG settings CSP_Strict (hard constraints only) and
CSP_HypIG (hard constraints + IG-weighted hypotheses).
"""

from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

from method.csp4sdg_avalonlogs import solve_instance


def _solve(inst):
    return inst["instance_id"], solve_instance(inst)


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: python3 -m method.predict <input_dir> <output_dir>")
    inp, out = Path(argv[1]), Path(argv[2])
    instances = json.loads((inp / "instances.json").read_text())["instances"]
    workers = int(os.environ.get("PREDICT_WORKERS", min(8, os.cpu_count() or 1)))
    if workers > 1:
        with Pool(workers) as pool:
            preds = dict(pool.imap(_solve, instances, chunksize=16))
    else:
        preds = dict(map(_solve, instances))
    out.mkdir(parents=True, exist_ok=True)
    (out / "predictions.json").write_text(json.dumps({"predictions": preds}))
    print(f"predicted {len(preds)} instances -> {out / 'predictions.json'}")


if __name__ == "__main__":
    main(sys.argv)
