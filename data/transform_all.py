"""
Transform all per-year combine CSVs (2020–2026) into a single combine_stats.csv.
Run from the nfl-scout-ai/ directory: python data/transform_all.py
"""
import csv
import re
from collections import Counter

YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

POSITION_MAP = {
    # Offense
    'QB': 'QB',
    'RB': 'RB', 'FB': 'RB',
    'WR': 'WR',
    'TE': 'TE',
    'OT': 'OL', 'G': 'OL', 'OG': 'OL', 'C': 'OL', 'OL': 'OL',
    # Defense
    'EDGE': 'DE', 'DE': 'DE', 'DL': 'DE', 'DT': 'DE',
    'LB': 'LB', 'ILB': 'LB', 'OLB': 'LB',
    'CB': 'CB', 'DB': 'CB',
    'SAF': 'S', 'SS': 'S', 'FS': 'S', 'S': 'S',
}

FIELDS = [
    'player_id', 'name', 'position', 'draft_year',
    'forty_yard', 'bench_reps', 'vertical_jump', 'broad_jump',
    'three_cone', 'shuttle', 'height_in', 'weight_lbs',
    'college', 'is_hof', 'draft_round', 'draft_pick',
]

ROUND_MAP = {
    '1st': 1, '2nd': 2, '3rd': 3, '4th': 4,
    '5th': 5, '6th': 6, '7th': 7,
}


def ht_to_in(ht: str) -> str:
    if not ht or '-' not in ht:
        return ''
    parts = ht.split('-')
    try:
        return str(int(parts[0]) * 12 + int(parts[1]))
    except Exception:
        return ''


def make_id(name: str, pos: str, year: int) -> str:
    s = name.lower()
    s = re.sub(r"[.']", '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'[^a-z0-9\-]', '', s)
    return f'{s}-{pos.lower()}-{year}'


def parse_draft(d: str):
    """
    Handles two formats:
      3-part: "SEA / 7th / 53"               (2026-style)
      4-part: "New England / 3rd / 87th pick / 2024"  (2020-2025-style)
    Returns (round_str, pick_str) or ('', '') if undrafted.
    """
    if not d or not d.strip():
        return '', ''
    parts = [p.strip() for p in d.split('/')]
    if len(parts) < 3:
        return '', ''
    rnd = ROUND_MAP.get(parts[1].strip(), '')
    pick_str = parts[2].strip()
    m = re.search(r'(\d+)', pick_str)
    pick = m.group(1) if m else ''
    return str(rnd), str(pick)


rows = []
seen_ids: set = set()
skipped_positions: list = []
year_counts: dict = {}

for year in YEARS:
    filename = f'data/{year}.csv'
    try:
        # utf-8-sig strips the BOM that Excel sometimes adds
        with open(filename, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                pos_raw = row.get('Pos', '').strip()
                if pos_raw not in POSITION_MAP:
                    skipped_positions.append(pos_raw)
                    continue
                pos = POSITION_MAP[pos_raw]

                # 2026.csv uses 'layer' as the player name column; all others use 'Player'
                name = (row.get('Player') or row.get('layer') or '').strip()
                if not name:
                    continue

                pid = make_id(name, pos, year)
                # Resolve rare same-name + same-position + same-year collisions
                base_pid = pid
                suffix = 1
                while pid in seen_ids:
                    pid = f'{base_pid}-{suffix}'
                    suffix += 1
                seen_ids.add(pid)

                draft_round, draft_pick = parse_draft(
                    row.get('Drafted (tm/rnd/yr)', '').strip()
                )

                rows.append({
                    'player_id': pid,
                    'name': name,
                    'position': pos,
                    'draft_year': year,
                    'forty_yard': row.get('40yd', '').strip(),
                    'bench_reps': row.get('Bench', '').strip(),
                    'vertical_jump': row.get('Vertical', '').strip(),
                    'broad_jump': row.get('Broad Jump', '').strip(),
                    'three_cone': row.get('3Cone', '').strip(),
                    'shuttle': row.get('Shuttle', '').strip(),
                    'height_in': ht_to_in(row.get('Ht', '').strip()),
                    'weight_lbs': row.get('Wt', '').strip(),
                    'college': row.get('School', '').strip(),
                    'is_hof': 'False',
                    'draft_round': draft_round,
                    'draft_pick': draft_pick,
                })
                count += 1
        year_counts[year] = count
    except FileNotFoundError:
        print(f'Warning: {filename} not found — skipping.')

with open('data/combine_stats.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)

print(f'Written {len(rows)} total players to combine_stats.csv')
for y, c in sorted(year_counts.items()):
    print(f'  {y}: {c} players')

pos_counts = Counter(r['position'] for r in rows)
print('By position:', dict(sorted(pos_counts.items())))

skipped_unique = sorted(set(p for p in skipped_positions if p))
if skipped_unique:
    print('Skipped positions (not in POSITION_MAP):', skipped_unique)
