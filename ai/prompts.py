SYSTEM_PROMPT = (
    "You are an NFL scout and talent evaluator with 20 years of experience.\n"
    "You analyze combine performance to grade players objectively using specific numbers.\n"
    "You are strictly position-aware: you NEVER compare a WR's 40-yard dash against an OL's average,\n"
    "or grade a QB by WR speed standards. Always use the positional benchmarks provided.\n"
    "You grade COMBINE ATHLETICISM ONLY — not career success, reputation, or fame.\n"
    "Tom Brady being the GOAT does not affect his combine grade.\n"
    "STAT DIRECTION — this is absolute and never reversed:\n"
    "  LOWER is better: 40-yard dash, 3-cone drill, shuttle run (faster time = better athlete).\n"
    "  HIGHER is better: bench press reps, vertical jump, broad jump (more output = better athlete).\n"
    "A player who runs a 4.30s 40 is faster than one who runs 4.60s. A 40\" vertical beats a 32\" vertical.\n"
    "You never fabricate statistics. If data is missing, say so explicitly in data_warning.\n"
    "Only name comparable players that appear in the provided data — never invent player names.\n"
    "Always respond in valid JSON matching the schema provided."
)

# Schema strings are VALUES substituted into templates — use literal braces, not {{ escapes.

GRADE_JSON_SCHEMA = (
    '{\n'
    '  "player_name": "string",\n'
    '  "position": "string (QB|RB|WR|TE|OL|DE|DT|LB|CB|S)",\n'
    '  "grade": "string (A+|A|A-|B+|B|B-|C+|C|C-|D|F)",\n'
    '  "score": 85,\n'
    '  "strengths": ["string", "string"],\n'
    '  "weaknesses": ["string"],\n'
    '  "justification": "string — 2-3 sentences citing specific stats",\n'
    '  "confidence": "string (high|medium|low)",\n'
    '  "data_warning": null\n'
    '}'
)

COMPARE_JSON_SCHEMA = (
    '{\n'
    '  "player1": {\n'
    '    "name": "string",\n'
    '    "position": "string",\n'
    '    "grade": "string (A+|A|A-|B+|B|B-|C+|C|C-|D|F)",\n'
    '    "score": 85,\n'
    '    "strengths": ["string"],\n'
    '    "weaknesses": ["string"]\n'
    '  },\n'
    '  "player2": {\n'
    '    "name": "string",\n'
    '    "position": "string",\n'
    '    "grade": "string (A+|A|A-|B+|B|B-|C+|C|C-|D|F)",\n'
    '    "score": 85,\n'
    '    "strengths": ["string"],\n'
    '    "weaknesses": ["string"]\n'
    '  },\n'
    '  "verdict": "string — name of better prospect or Push",\n'
    '  "verdict_reason": "string — 2-3 sentences citing specific numbers",\n'
    '  "head_to_head": [\n'
    '    {"stat": "string", "player1_val": "string", "player2_val": "string", "winner": "string"}\n'
    '  ],\n'
    '  "same_position": true,\n'
    '  "data_warning": null\n'
    '}'
)

CREATE_JSON_SCHEMA = (
    '{\n'
    '  "position": "string",\n'
    '  "grade": "string (A+|A|A-|B+|B|B-|C+|C|C-|D|F)",\n'
    '  "score": 85,\n'
    '  "strengths": ["string"],\n'
    '  "weaknesses": ["string"],\n'
    '  "comparable_players": [\n'
    '    {"name": "string", "similarity": "string"}\n'
    '  ],\n'
    '  "justification": "string — 2-3 sentences citing specific numbers",\n'
    '  "draft_projection": "string"\n'
    '}'
)

GRADE_USER_TEMPLATE = """Evaluate {name}'s NFL combine performance as a {position}.

PLAYER DATA (retrieved from vector store):
{retrieved_combine_text}

POSITIONAL BENCHMARKS (average for {position}):
40-yard dash: {avg_forty}s [LOWER=better] | Bench: {avg_bench} reps [HIGHER=better] | Vertical: {avg_vertical}" [HIGHER=better]
Broad jump: {avg_broad}" [HIGHER=better] | 3-cone: {avg_three_cone}s [LOWER=better] | Shuttle: {avg_shuttle}s [LOWER=better]

ELITE THRESHOLDS (top 10% for {position}):
40-yard dash: {elite_forty}s [LOWER=better] | Bench: {elite_bench} reps [HIGHER=better] | Vertical: {elite_vertical}" [HIGHER=better]

POSITION PEERS FOR CONTEXT:
{peers_text}

GRADED EXAMPLES (use this scale):
- Barry Sanders (RB): 4.37 40, 23 bench, 41" vertical -> A+ (generational athleticism for RB)
- Tom Brady (QB): 5.28 40, 24 bench, 24.5" vertical -> C (below-average QB combine, not compared to WR standards)

TASK: Assign a letter grade (A+ through F) and numeric score (0-100) for this player's
combine performance AT THEIR POSITION ONLY. Identify 2-3 strengths and 1-2 weaknesses.
A stat is a STRENGTH if it beats the positional average (lower time, or higher reps/inches).
A stat is a WEAKNESS only if it falls short of the positional average — not merely below elite.
Write 2-3 sentences of justification citing specific numbers from PLAYER DATA.
If any stats are missing, note this in data_warning.

Respond in this exact JSON schema:
{json_schema}"""

COMPARE_USER_TEMPLATE = """Compare the NFL combine performance of {name1} ({position1}) and {name2} ({position2}).

PLAYER 1 — {name1} ({position1}):
{player1_combine_text}

PLAYER 1 BENCHMARKS (average for {position1}):
{benchmarks1_text}
[40-yard/3-cone/shuttle: LOWER=better | bench/vertical/broad: HIGHER=better]

PLAYER 2 — {name2} ({position2}):
{player2_combine_text}

PLAYER 2 BENCHMARKS (average for {position2}):
{benchmarks2_text}
[40-yard/3-cone/shuttle: LOWER=better | bench/vertical/broad: HIGHER=better]

TASK:
1. Grade each player's combine performance AGAINST THEIR OWN POSITION BENCHMARKS ONLY.
2. Build a head-to-head stat comparison (only include stats where at least one player has data).
3. Name the better combine prospect as the verdict, or "Push" if too close to call.
4. Write 2-3 sentences explaining the verdict citing specific numbers.
If positions differ, grade each against their own standard and note this.
If any stats are missing, note in data_warning.

Respond in this exact JSON schema:
{json_schema}"""

CREATE_USER_TEMPLATE = """A user has entered the following combine numbers for position: {position}

USER'S COMBINE STATS:
{user_stats_text}

POSITIONAL BENCHMARKS (average for {position}):
{benchmarks_text}

COMPARABLE REAL PROSPECTS AT THIS POSITION (from dataset — only name these players):
{comparables_text}

TASK: Grade this user's athleticism as an NFL prospect at {position}.
Compare their numbers directly against the positional benchmarks.
Name 2-3 comparable players from ONLY the list above — do not invent player names.
Give a draft projection based on athleticism alone.
Write 2-3 sentences of justification citing specific numbers.

Respond in this exact JSON schema:
{json_schema}"""


def format_prompt(template: str, **kwargs) -> str:
    return template.format(**kwargs)
