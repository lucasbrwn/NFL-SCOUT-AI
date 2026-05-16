import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv
from openai import APIError, OpenAI

from rag.retriever import get_player_combine
from ai.prompts import (
    SYSTEM_PROMPT,
    COMPARE_USER_TEMPLATE,
    COMPARE_JSON_SCHEMA,
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


def _format_benchmark_text(bench: dict) -> str:
    return (
        f"40-yard dash: {bench.get('avg_forty', 'N/A')}s | "
        f"Bench: {bench.get('avg_bench', 'N/A')} reps | "
        f"Vertical: {bench.get('avg_vertical', 'N/A')}\" | "
        f"Broad: {bench.get('avg_broad', 'N/A')}\" | "
        f"3-cone: {bench.get('avg_three_cone', 'N/A')}s | "
        f"Shuttle: {bench.get('avg_shuttle', 'N/A')}s\n"
        f"Elite: 40-yard: {bench.get('elite_forty', 'N/A')}s | "
        f"Bench: {bench.get('elite_bench', 'N/A')} reps | "
        f"Vertical: {bench.get('elite_vertical', 'N/A')}\""
    )


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


def compare_players(
    name1: str,
    name2: str,
    position1: str = None,
    position2: str = None,
) -> dict:
    records1 = get_player_combine(name1, position1)
    if position1 and records1 and not _name_matches(name1, records1[0]["metadata"].get("name", "")):
        unfiltered1 = get_player_combine(name1, position=None)
        if unfiltered1 and _name_matches(name1, unfiltered1[0]["metadata"].get("name", "")):
            records1 = unfiltered1
    if position1 and not records1:
        unfiltered1 = get_player_combine(name1, position=None)
        if unfiltered1 and _name_matches(name1, unfiltered1[0]["metadata"].get("name", "")):
            records1 = unfiltered1

    records2 = get_player_combine(name2, position2)
    if position2 and records2 and not _name_matches(name2, records2[0]["metadata"].get("name", "")):
        unfiltered2 = get_player_combine(name2, position=None)
        if unfiltered2 and _name_matches(name2, unfiltered2[0]["metadata"].get("name", "")):
            records2 = unfiltered2
    if position2 and not records2:
        unfiltered2 = get_player_combine(name2, position=None)
        if unfiltered2 and _name_matches(name2, unfiltered2[0]["metadata"].get("name", "")):
            records2 = unfiltered2

    warnings = []

    if not records1:
        warnings.append(f"Player '{name1}' not found in dataset.")
        inferred_pos1 = position1 or "WR"
        p1_text = f"No data found for {name1}."
    else:
        top1_name = records1[0]["metadata"].get("name", "")
        if not _name_matches(name1, top1_name):
            warnings.append(f"'{name1}' not found; closest match: {top1_name}.")
        inferred_pos1 = position1 or records1[0]["metadata"].get("position", "WR")
        p1_text = "\n".join(r["text"] for r in records1)

    if not records2:
        warnings.append(f"Player '{name2}' not found in dataset.")
        inferred_pos2 = position2 or "WR"
        p2_text = f"No data found for {name2}."
    else:
        top2_name = records2[0]["metadata"].get("name", "")
        if not _name_matches(name2, top2_name):
            warnings.append(f"'{name2}' not found; closest match: {top2_name}.")
        inferred_pos2 = position2 or records2[0]["metadata"].get("position", "WR")
        p2_text = "\n".join(r["text"] for r in records2)

    bench1 = _load_benchmark(inferred_pos1)
    bench2 = _load_benchmark(inferred_pos2)

    user_prompt = format_prompt(
        COMPARE_USER_TEMPLATE,
        name1=name1,
        position1=inferred_pos1,
        player1_combine_text=p1_text,
        benchmarks1_text=_format_benchmark_text(bench1),
        name2=name2,
        position2=inferred_pos2,
        player2_combine_text=p2_text,
        benchmarks2_text=_format_benchmark_text(bench2),
        json_schema=COMPARE_JSON_SCHEMA,
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

    if result.get("player1"):
        result["player1"]["position"] = inferred_pos1
    if result.get("player2"):
        result["player2"]["position"] = inferred_pos2

    if warnings:
        existing = result.get("data_warning")
        combined = " ".join(warnings)
        result["data_warning"] = (combined + " " + existing) if existing else combined

    return result


if __name__ == "__main__":
    import pprint

    print("=== compare_players('Zachariah Branch', 'Malik Benson') ===")
    pprint.pprint(compare_players("Zachariah Branch", "Malik Benson"))
