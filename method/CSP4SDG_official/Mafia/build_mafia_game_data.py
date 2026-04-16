"""
For every verdict JSON in mafia_dataset/{Truth,Lie}/, locate the matching raw
folder in mafia_dataset_raw/, parse node.csv & info.csv, sort by timestamp,
segment by every 2 deaths (= one Mafia "day"), and write a structured game
JSON to mafia_dataset_processed/{Truth,Lie}/.

Usage:
    python build_mafia_game_data.py mafia_dataset_raw mafia_dataset_verdict mafia_dataset
"""

import os, sys, json, re
from datetime import timedelta, datetime
from pathlib import Path
import pandas as pd

# ---------- helpers: timestamp parsing ----------
_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2}(?:\.\d+)?)$")
def parse_offset(s):
    m=_RE.match(str(s).strip());                      # "H:MM:SS" or "MM:SS"
    if not m: return None
    h=int(m.group(1) or 0); mnt=int(m.group(2)); sec=float(m.group(3))
    return timedelta(hours=h, minutes=mnt, seconds=sec)

def read_csv(path): return pd.read_csv(path)

def build_players(node_df):
    players=[]
    for _,row in node_df.iterrows():
        name=str(row.get("property1") or "").strip()
        if not name: continue
        role = "bystander" if str(row.get("type")).lower()=="bystander" else "mafioso"
        players.append({"name":name, "role":role})
    return players

def load_rows(info_df):
    base = datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)
    rows=[]
    for _,r in info_df.iterrows():
        typ=str(r["type"])
        raw_ts=r["creation_time"]
        try: ts=pd.to_datetime(raw_ts)
        except: ts=base + (parse_offset(raw_ts) or timedelta())
        text=str(r.get("contents","")).replace("\n"," ")
        if typ=="text":
            speaker=str(r.get("sender")).strip(); rows.append((ts,speaker,text))
        elif typ=="vote":  rows.append((ts,"system",f"Vote: {text}"))
        elif typ=="info":  rows.append((ts,"system",text))
    rows.sort(key=lambda x:x[0])
    return rows

def add_deaths(rows,node_df):
    base=datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)
    for _,r in node_df.iterrows():
        name=str(r.get("property1") or "").strip()
        raw=r.get("property3");  ts=None
        if pd.notna(raw):
            try: ts=pd.to_datetime(raw)
            except: ts=base + (parse_offset(raw) or timedelta())
            rows.append((ts,"system",f"Death: {name}"))
    rows.sort(key=lambda x:x[0])

def segment(rows):
    # One "day" = from 1st death to before (n+2)th death
    death_idx=[i for i,(_,spk,txt) in enumerate(rows) if txt.startswith("Death")]
    if not death_idx: return [(1,rows)]
    segs=[]; death_times=[rows[i][0] for i in death_idx]
    for i in range(0,len(death_times),2):
        start=death_times[i]
        end  =death_times[i+2] if i+2<len(death_times) else None
        chunk=[row for row in rows if row[0]>=start and (end is None or row[0]<end)]
        segs.append(chunk)
    return list(enumerate(segs,start=1))

def rows_to_transcript(chunk):
    return [{"ts":row[0].isoformat(timespec="seconds"),
             "speaker":row[1],
             "text":row[2]} for row in chunk]

# ---------- main per-game ----------
def process_game(raw_dir:Path, verdict_path:Path, out_dir:Path):
    node_csv=raw_dir/"node.csv"; info_csv=raw_dir/"info.csv"
    if not node_csv.exists() or not info_csv.exists():
        print(f"[skip] {raw_dir.name}: csv missing"); return
    node_df=read_csv(node_csv); info_df=read_csv(info_csv)

    players  = build_players(node_df)
    rows     = load_rows(info_df)
    add_deaths(rows,node_df)
    rounds   = [{"round":idx,"transcript":rows_to_transcript(chunk)}
                for idx,chunk in segment(rows)]

    game_json={"players":players,"rounds":rounds}

    out_dir.mkdir(parents=True,exist_ok=True)
    out_fp=out_dir/f"{raw_dir.name}.json"
    with open(out_fp, "w", encoding="utf-8") as f:
        json.dump(game_json, f, indent=2, ensure_ascii=False)
    print(f"[OK] {out_fp.relative_to(out_dir.parent)}")

# ---------- entry ----------
if __name__=="__main__":
    if len(sys.argv)!=4:
        print("Usage: python build_mafia_game_json.py <raw_root> <verdict_root> <out_root>")
        sys.exit(1)
    raw_root   = Path(sys.argv[1]).resolve()
    verdict_root=Path(sys.argv[2]).resolve()
    out_root   = Path(sys.argv[3]).resolve()

    for cond in ("Truth","Lie"):
        for vfp in (verdict_root/cond).glob("*_verdict.json"):
            gid = vfp.stem.replace("_verdict","")
            raw_dir = raw_root/gid
            if not raw_dir.exists():
                print(f"[miss] raw dir {gid}")
                continue
            process_game(raw_dir, vfp, out_root/cond)
