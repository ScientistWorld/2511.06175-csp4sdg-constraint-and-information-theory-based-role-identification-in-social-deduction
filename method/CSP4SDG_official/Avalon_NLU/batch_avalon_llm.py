"""
---------------------------------
Recursively process all raw Avalon logs inside:

    <dataset_dir>/Truth/*.json
    <dataset_dir>/Lie/*.json

For each file, call avalon_llm.process_game()
and move the resulting *_constraints.json into:

    <out_dir>/Truth/
    <out_dir>/Lie/

Usage:
    python batch_avalon_llm.py <dataset_dir> <out_dir>
"""

import sys
import importlib
from pathlib import Path

avalon_llm = importlib.import_module("avalon_llm")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path

def process_subdir(in_dir: Path, out_dir: Path):
    """
    Process every .json in in_dir, except *_constraints.json,
    writing *_constraints.json to out_dir.
    """
    ensure_dir(out_dir)
    # collect only raw game files (exclude constraints outputs)
    for fp in in_dir.glob("*.json"):
        if fp.stem.endswith("_constraints"):
            continue  # skip previously generated files
        # run the single-file conversion
        avalon_llm.process_game(fp.as_posix(), use_ig=True)
        # expected output file next to fp
        produced = fp.with_name(fp.stem + "_constraints.json")
        if produced.exists():
            produced.rename(out_dir / produced.name)
            print(f"[OK] {fp.name} → {out_dir / produced.name}")
        else:
            print(f"[WARN] expected output not found for {fp.name}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python batch_avalon_llm.py <dataset_dir> <out_dir>")
        sys.exit(1)

    data_dir = Path(sys.argv[1]).resolve()
    out_dir  = Path(sys.argv[2]).resolve()

    for tag in ("Truth", "Lie"):
        in_sub  = data_dir / tag
        out_sub = out_dir  / tag
        if not in_sub.exists():
            print(f"[SKIP] {in_sub} not found")
            continue
        process_subdir(in_sub, out_sub)

    print("Batch processing complete.")
