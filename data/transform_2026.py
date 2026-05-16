import csv
import re
from collections import Counter

POSITION_MAP = {
    'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE',
    'OT': 'OL', 'G': 'OL', 'C': 'OL',
    'LB': 'LB', 'CB': 'CB', 'SAF': 'S', 'EDGE': 'DE',
}

def ht_to_in(ht):
    if not ht or '-' not in ht:
        return ''
    parts = ht.split('-')
    try:
        return str(int(parts[0]) * 12 + int(parts[1]))
    except Exception:
        return ''

def make_id(name, pos):
    s = name.lower()
    s = re.sub(r"[.']", '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'[^a-z0-9\-]', '', s)
    return f'{s}-{pos.lower()}'

def parse_draft(d):
    if not d or d == '-9999':
        return '', ''
    parts = [p.strip() for p in d.split('/')]
    if len(parts) < 3:
        return '', ''
    rmap = {'1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5, '6th': 6, '7th': 7}
    rnd = rmap.get(parts[1], '')
    m = re.search(r'(\d+)', parts[2])
    pick = m.group(1) if m else ''
    return str(rnd), str(pick)

rows = []
seen_ids = {}

with open('data/2026.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos_raw = row.get('Pos', '').strip()
        if pos_raw not in POSITION_MAP:
            continue
        pos = POSITION_MAP[pos_raw]
        name = row.get('layer', '').strip()
        if not name:
            continue

        pid = make_id(name, pos)
        if pid in seen_ids:
            seen_ids[pid] += 1
            pid = f'{pid}-{seen_ids[pid]}'
        else:
            seen_ids[pid] = 1

        draft_round, draft_pick = parse_draft(row.get('Drafted (tm/rnd/yr)', '').strip())
        rows.append({
            'player_id': pid,
            'name': name,
            'position': pos,
            'draft_year': 2026,
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

fields = [
    'player_id', 'name', 'position', 'draft_year',
    'forty_yard', 'bench_reps', 'vertical_jump', 'broad_jump',
    'three_cone', 'shuttle', 'height_in', 'weight_lbs',
    'college', 'is_hof', 'draft_round', 'draft_pick',
]

with open('data/combine_stats.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

pos_counts = Counter(r['position'] for r in rows)
print(f'Written {len(rows)} players to combine_stats.csv')
print('By position:', dict(sorted(pos_counts.items())))
skipped = [row.get('Pos', '') for row in csv.DictReader(open('data/2026.csv', encoding='utf-8'))
           if row.get('Pos', '').strip() not in POSITION_MAP]
print('Skipped positions:', sorted(set(skipped)))
