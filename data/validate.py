import sys
import pandas as pd

VALID_POSITIONS = {"QB", "RB", "WR", "TE", "OL", "DE", "LB", "CB", "S"}
errors = []

# Load files
try:
    players = pd.read_csv("data/combine_stats.csv")
except FileNotFoundError:
    print("ERROR: data/combine_stats.csv not found")
    sys.exit(1)

try:
    benchmarks = pd.read_csv("data/positional_benchmarks.csv")
except FileNotFoundError:
    print("ERROR: data/positional_benchmarks.csv not found")
    sys.exit(1)

# Check 1: unique player_id
dupes = players[players.duplicated("player_id", keep=False)]["player_id"].unique()
if len(dupes):
    errors.append(f"Duplicate player_id values: {list(dupes)}")

# Check 2: valid position values
bad_positions = players[~players["position"].isin(VALID_POSITIONS)]["position"].unique()
if len(bad_positions):
    errors.append(f"Invalid position values: {list(bad_positions)}")

# Check 3: is_hof is Python-parseable boolean
bad_hof = players[~players["is_hof"].isin([True, False])]["is_hof"].unique()
if len(bad_hof):
    errors.append(f"is_hof contains non-boolean values: {list(bad_hof)}")

# Check 4: positional_benchmarks has exactly 9 rows
if len(benchmarks) != 9:
    errors.append(f"positional_benchmarks.csv has {len(benchmarks)} rows (expected 9)")

# Report
if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"OK: {len(players)} players loaded, all checks passed.")
    print(f"  Positions: { {p: int((players['position']==p).sum()) for p in sorted(VALID_POSITIONS)} }")
    print(f"  HOF players: {players['is_hof'].sum()}")
    print(f"  Benchmarks rows: {len(benchmarks)}")
