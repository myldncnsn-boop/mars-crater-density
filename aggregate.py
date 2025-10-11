# aggregate.py
import sys, re, csv, pandas as pd
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("run_2_tiles")
pattern = "**/*.csv"

print(f"[info] Searching: {root}/{pattern}")
files = list(root.glob(pattern))
print(f"[info] Found {len(files)} CSV(s). Showing up to 10:")
for p in files[:10]:
    print("  -", p)

# columns we keep (first 19, up to 'Source')
keep_cols = ["Name","Area","Binning","d_min","d_max","Method","Resurf","N","N_event",
             "Age","Age-","Age+","a0","a0-","a0+","N(1)","N(1)-","N(1)+","Source"]

rows = []
pat = re.compile(r"tile_lat(?P<lat>[-+0-9.]+)_lon(?P<lon>[-+0-9.]+)", re.I)

for path in files:
    m = pat.search(path.name)
    if not m:
        # skip files that don't encode the centroid in the filename
        continue
    lat = float(m.group("lat")); lon = float(m.group("lon"))

    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            # Skip the first two preface lines
            next(r, None)
            next(r, None)
            # Read header line (we won't rely on its length, we’ll slice)
            header = next(r, None)
            if header is None:
                continue
            # Read all remaining data rows (usually just 1)
            for row in r:
                if not row:
                    continue
                # Take only the first 19 fields (through 'Source')
                row19 = row[:19]
                if len(row19) < 19:
                    # malformed row; skip
                    continue
                rec = dict(zip(keep_cols, row19))
                # Attach centroid + stable tile id
                rec["centroid_lat"] = lat
                rec["centroid_lon"] = lon
                rec["tile_id"] = f"lat{lat:+07.2f}_lon{lon:+08.2f}"
                rows.append(rec)
    except Exception as e:
        print(f"[warn] Could not read {path.name}: {e}")

if rows:
    df = pd.DataFrame(rows)
    out = Path("mars_age_tiles_agg_run2.csv")
    df.to_csv(out, index=False)
    print(f"[ok] Aggregated {len(df)} rows from {len(set((r['tile_id'] for r in rows)))} tiles → {out}")
else:
    print("[warn] No matching tile CSVs or no usable rows found.")
