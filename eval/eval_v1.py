"""
V1 baseline eval — no RAG.
The LLM receives only: player name, position, and positional benchmarks from the CSV.
No ChromaDB retrieval, no peer comparisons, no name-matching guard for unknown players.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from openai import OpenAI
from ai.prompts import (
    SYSTEM_PROMPT,
    GRADE_USER_TEMPLATE,
    GRADE_JSON_SCHEMA,
    COMPARE_USER_TEMPLATE,
    COMPARE_JSON_SCHEMA,
    CREATE_USER_TEMPLATE,
    CREATE_JSON_SCHEMA,
    format_prompt,
)

_PROJECT_ROOT = Path(__file__).parent.parent
_BENCHMARKS_PATH = _PROJECT_ROOT / "data" / "positional_benchmarks.csv"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


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


# ---------------------------------------------------------------------------
# V1 pipelines — no vector store, no name-match guard
# ---------------------------------------------------------------------------

def grade_player(name: str, position: str = None) -> dict:
    inferred_position = position or "WR"
    bench = _load_benchmark(inferred_position)

    user_prompt = format_prompt(
        GRADE_USER_TEMPLATE,
        name=name,
        position=inferred_position,
        retrieved_combine_text="No player data retrieved — V1 baseline relies on LLM knowledge only.",
        avg_forty=bench.get("avg_forty", "N/A"),
        avg_bench=bench.get("avg_bench", "N/A"),
        avg_vertical=bench.get("avg_vertical", "N/A"),
        avg_broad=bench.get("avg_broad", "N/A"),
        avg_three_cone=bench.get("avg_three_cone", "N/A"),
        avg_shuttle=bench.get("avg_shuttle", "N/A"),
        elite_forty=bench.get("elite_forty", "N/A"),
        elite_bench=bench.get("elite_bench", "N/A"),
        elite_vertical=bench.get("elite_vertical", "N/A"),
        peers_text="No peer data available in V1 baseline.",
        json_schema=GRADE_JSON_SCHEMA,
    )
    return _call_openai(user_prompt)


def compare_players(name1: str, name2: str,
                    position1: str = None, position2: str = None) -> dict:
    inferred_pos1 = position1 or "WR"
    inferred_pos2 = position2 or "WR"
    bench1 = _load_benchmark(inferred_pos1)
    bench2 = _load_benchmark(inferred_pos2)

    user_prompt = format_prompt(
        COMPARE_USER_TEMPLATE,
        name1=name1,
        position1=inferred_pos1,
        player1_combine_text=f"No data retrieved for {name1} — V1 baseline relies on LLM knowledge only.",
        benchmarks1_text=_format_benchmark_text(bench1),
        name2=name2,
        position2=inferred_pos2,
        player2_combine_text=f"No data retrieved for {name2} — V1 baseline relies on LLM knowledge only.",
        benchmarks2_text=_format_benchmark_text(bench2),
        json_schema=COMPARE_JSON_SCHEMA,
    )
    return _call_openai(user_prompt)


def create_player(position: str, forty_yard: float = None, bench_reps: int = None,
                  vertical_jump: float = None, broad_jump: int = None,
                  three_cone: float = None, shuttle: float = None,
                  height_in: int = None, weight_lbs: int = None) -> dict:
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
        return {"data_warning": "Please provide at least one combine stat.", "grade": None}

    user_stats_text = "\n".join(f"  {k}: {v}" for k, v in numeric_stats.items())
    bench = _load_benchmark(position)

    user_prompt = format_prompt(
        CREATE_USER_TEMPLATE,
        position=position,
        user_stats_text=user_stats_text,
        benchmarks_text=_format_benchmark_text(bench),
        comparables_text="No comparable prospects available in V1 baseline.",
        json_schema=CREATE_JSON_SCHEMA,
    )
    return _call_openai(user_prompt)


# ---------------------------------------------------------------------------
# Eval logic (same as eval.py)
# ---------------------------------------------------------------------------

GRADE_ORDER = ["F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]


def grade_in_range(actual, expected_range):
    if actual not in GRADE_ORDER:
        return False
    actual_idx = GRADE_ORDER.index(actual)
    for expected in expected_range:
        if expected not in GRADE_ORDER:
            continue
        if abs(actual_idx - GRADE_ORDER.index(expected)) <= 1:
            return True
    return False


def evaluate_grade(result, expected):
    if expected.get("data_warning") == "not_null":
        if result.get("data_warning"):
            return True, f"data_warning correctly set: '{result['data_warning']}'"
        return False, f"Expected data_warning but got confident grade: {result.get('grade')}"

    actual_grade = result.get("grade", "")
    if not grade_in_range(actual_grade, expected["grade_range"]):
        return False, f"Grade '{actual_grade}' not within 1 step of {expected['grade_range']}"

    expected_pos = expected.get("position")
    actual_pos = result.get("position", "")
    if expected_pos and actual_pos != expected_pos:
        return False, f"Wrong position: got '{actual_pos}', expected '{expected_pos}'"

    return True, f"Grade '{actual_grade}' in range {expected['grade_range']}, position '{actual_pos}'"


def evaluate_compare(result, expected):
    if not result.get("player1") or not result.get("player2"):
        return False, "Missing player1 or player2 in response"

    p1_pos = (result.get("player1") or {}).get("position", "")
    p2_pos = (result.get("player2") or {}).get("position", "")

    if "player1_position" in expected and p1_pos != expected["player1_position"]:
        return False, f"Player1 position: got '{p1_pos}', expected '{expected['player1_position']}'"
    if "player2_position" in expected and p2_pos != expected["player2_position"]:
        return False, f"Player2 position: got '{p2_pos}', expected '{expected['player2_position']}'"

    if "same_position" in expected:
        actual_same = result.get("same_position")
        if actual_same != expected["same_position"]:
            return False, f"same_position: got {actual_same}, expected {expected['same_position']}"

    actual_verdict = result.get("verdict", "")

    if "verdict" in expected:
        if actual_verdict != expected["verdict"]:
            return False, f"Verdict '{actual_verdict}' != expected '{expected['verdict']}'"
        return True, f"Verdict '{actual_verdict}' correct, positions p1='{p1_pos}' p2='{p2_pos}'"

    if "verdict_options" in expected:
        if actual_verdict not in expected["verdict_options"]:
            return False, f"Verdict '{actual_verdict}' not in {expected['verdict_options']}"
        return True, f"Verdict '{actual_verdict}' accepted, positions p1='{p1_pos}' p2='{p2_pos}'"

    return True, f"Positions p1='{p1_pos}' p2='{p2_pos}', same_position={result.get('same_position')}"


def evaluate_create(result, expected):
    if expected.get("data_warning") is not None:
        if result.get("data_warning"):
            return True, f"data_warning correctly set: '{result['data_warning']}'"
        return False, f"Expected data_warning for null-stat input but got grade: {result.get('grade')}"

    actual_grade = result.get("grade", "")
    if not grade_in_range(actual_grade, expected["grade_range"]):
        return False, f"Grade '{actual_grade}' not within 1 step of {expected['grade_range']}"

    expected_pos = expected.get("position")
    actual_pos = result.get("position", "")
    if expected_pos and actual_pos != expected_pos:
        return False, f"Wrong position: got '{actual_pos}', expected '{expected_pos}'"

    return True, f"Grade '{actual_grade}' in range {expected['grade_range']}"


def run_eval():
    cases_path = Path(__file__).parent / "test_cases.json"
    with open(cases_path) as f:
        test_cases = json.load(f)

    results = []
    passed = 0

    for tc in test_cases:
        tc_id = tc["id"]
        feature = tc["feature"]
        inp = tc["input"]
        expected = tc["expected"]

        try:
            if feature == "grade":
                result = grade_player(inp["name"], inp.get("position"))
                ok, reason = evaluate_grade(result, expected)

            elif feature == "compare":
                result = compare_players(
                    inp["name1"], inp["name2"],
                    inp.get("position1"), inp.get("position2")
                )
                ok, reason = evaluate_compare(result, expected)

            elif feature == "create":
                stat_keys = ["forty_yard", "bench_reps", "vertical_jump", "broad_jump",
                             "three_cone", "shuttle", "height_in", "weight_lbs"]
                stats = {k: inp[k] for k in stat_keys if k in inp}
                result = create_player(position=inp["position"], **stats)
                ok, reason = evaluate_create(result, expected)

            else:
                ok, reason = False, f"Unknown feature: {feature}"
                result = {}

        except Exception as e:
            ok, reason = False, f"Exception: {e}"
            result = {}

        status = "PASS" if ok else "FAIL"
        print(f"{tc_id} [{status}] {reason}")
        if ok:
            passed += 1
        results.append({
            "id": tc_id,
            "feature": feature,
            "description": tc.get("description", ""),
            "passed": ok,
            "reason": reason,
            "result": result,
        })

    total = len(test_cases)
    accuracy = passed / total
    print(f"\nAccuracy: {passed}/{total} = {accuracy:.2f} ({accuracy*100:.0f}%)")

    os.makedirs(Path(__file__).parent / "results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(__file__).parent / "results" / f"run_v1_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump({
            "version": "V1",
            "timestamp": timestamp,
            "accuracy": round(accuracy, 4),
            "passed": passed,
            "total": total,
            "results": results,
        }, f, indent=2)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    run_eval()
