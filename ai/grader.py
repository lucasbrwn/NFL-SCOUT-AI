import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv
from openai import APIError, OpenAI

from rag.retriever import get_player_combine, get_position_peers
from ai.prompts import (
    SYSTEM_PROMPT,
    GRADE_USER_TEMPLATE,
    GRADE_JSON_SCHEMA,
    format_prompt,
)

load_dotenv()

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BENCHMARKS_PATH = os.path.join(_PROJECT_ROOT, "data", "positional_benchmarks.csv")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _load_benchmark(position: str) -> dict:
    df = pd.read_csv(_BENCHMARKS_PATH)
    row = df[df["position"] == position]
    return row.iloc[0].to_dict() if not row.empty else {}


def _name_matches(query: str, retrieved_name: str) -> bool:
    query_parts = query.lower().split()
    retrieved_parts = retrieved_name.lower().split()
    if not query_parts or not retrieved_parts:
        return False
    query_last = query_parts[-1]
    return len(query_last) > 2 and query_last == retrieved_parts[-1]


def _call_openai(prompt: str) -> dict:
    resp = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=800,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def grade_player(name: str, position: str = None) -> dict:
    records = get_player_combine(name, position)

    data_warning = None

    # If a position filter was applied but the top result doesn't name-match,
    # retry without the filter so the actual player isn't excluded by position.
    if position and records and not _name_matches(name, records[0]["metadata"].get("name", "")):
        unfiltered = get_player_combine(name, position=None)
        if unfiltered and _name_matches(name, unfiltered[0]["metadata"].get("name", "")):
            records = unfiltered

    # If the position filter returned zero results (player indexed under a different
    # position tag), retry without filter before giving up.
    if position and not records:
        unfiltered = get_player_combine(name, position=None)
        if unfiltered and _name_matches(name, unfiltered[0]["metadata"].get("name", "")):
            records = unfiltered

    if not records:
        data_warning = "Player not found in dataset"
        inferred_position = position or "WR"
        retrieved_text = "No player data found in vector store."
    else:
        top_name = records[0]["metadata"].get("name", "")
        if not _name_matches(name, top_name):
            data_warning = f"Exact player '{name}' not found. Closest dataset match: {top_name}."
        inferred_position = position or records[0]["metadata"].get("position", "WR")
        retrieved_text = "\n".join(r["text"] for r in records)

    peers = get_position_peers(inferred_position, n=5)
    peers_text = "\n".join(r["text"] for r in peers) if peers else "No peer data available."

    bench = _load_benchmark(inferred_position)

    user_prompt = format_prompt(
        GRADE_USER_TEMPLATE,
        name=name,
        position=inferred_position,
        retrieved_combine_text=retrieved_text,
        avg_forty=bench.get("avg_forty", "N/A"),
        avg_bench=bench.get("avg_bench", "N/A"),
        avg_vertical=bench.get("avg_vertical", "N/A"),
        avg_broad=bench.get("avg_broad", "N/A"),
        avg_three_cone=bench.get("avg_three_cone", "N/A"),
        avg_shuttle=bench.get("avg_shuttle", "N/A"),
        elite_forty=bench.get("elite_forty", "N/A"),
        elite_bench=bench.get("elite_bench", "N/A"),
        elite_vertical=bench.get("elite_vertical", "N/A"),
        peers_text=peers_text,
        json_schema=GRADE_JSON_SCHEMA,
    )

    try:
        result = _call_openai(user_prompt)
    except APIError as e:
        raise Exception(f"OpenAI API error: {e}") from e
    except json.JSONDecodeError:
        try:
            result = _call_openai(user_prompt)
        except json.JSONDecodeError as exc:
            raise Exception("Model returned invalid JSON") from exc

    result["position"] = inferred_position

    if data_warning:
        existing = result.get("data_warning")
        result["data_warning"] = (data_warning + " " + existing) if existing else data_warning

    return result


if __name__ == "__main__":
    import pprint

    print("=== grade_player('Zachariah Branch') ===")
    pprint.pprint(grade_player("Zachariah Branch"))
