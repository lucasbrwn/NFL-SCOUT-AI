import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv
from openai import APIError, OpenAI

from rag.retriever import get_position_peers
from ai.prompts import (
    SYSTEM_PROMPT,
    CREATE_USER_TEMPLATE,
    CREATE_JSON_SCHEMA,
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


def create_player(
    position: str,
    forty_yard: float = None,
    bench_reps: int = None,
    vertical_jump: float = None,
    broad_jump: int = None,
    three_cone: float = None,
    shuttle: float = None,
    height_in: int = None,
    weight_lbs: int = None,
) -> dict:
    stat_map = {
        "40-yard dash": forty_yard,
        "Bench reps": bench_reps,
        "Vertical jump": vertical_jump,
        "Broad jump": broad_jump,
        "3-cone drill": three_cone,
        "Shuttle": shuttle,
        "Height (in)": height_in,
        "Weight (lbs)": weight_lbs,
    }
    numeric_stats = {k: v for k, v in stat_map.items() if v is not None}

    if not numeric_stats:
        return {
            "data_warning": "Please provide at least one combine stat.",
            "grade": None,
        }

    user_stats_text = "\n".join(f"  {k}: {v}" for k, v in numeric_stats.items())

    peers = get_position_peers(position, n=5)
    comparables_text = (
        "\n".join(r["text"] for r in peers) if peers else "No comparable prospects found."
    )

    bench = _load_benchmark(position)

    user_prompt = format_prompt(
        CREATE_USER_TEMPLATE,
        position=position,
        user_stats_text=user_stats_text,
        benchmarks_text=_format_benchmark_text(bench),
        comparables_text=comparables_text,
        json_schema=CREATE_JSON_SCHEMA,
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

    return result


if __name__ == "__main__":
    import pprint

    print("=== create_player('WR', forty_yard=4.35, bench_reps=12, vertical_jump=42.0, weight_lbs=195) ===")
    pprint.pprint(
        create_player("WR", forty_yard=4.35, bench_reps=12, vertical_jump=42.0, weight_lbs=195)
    )
