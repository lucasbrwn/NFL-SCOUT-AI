import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from ai.grader import grade_player
from ai.compare import compare_players
from ai.create_player import create_player

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
    # TC05: unknown player — pass only if data_warning is set
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

    # Exact verdict match
    if "verdict" in expected:
        if actual_verdict != expected["verdict"]:
            return False, f"Verdict '{actual_verdict}' != expected '{expected['verdict']}'"
        return True, f"Verdict '{actual_verdict}' correct, positions p1='{p1_pos}' p2='{p2_pos}'"

    # One-of verdict match
    if "verdict_options" in expected:
        if actual_verdict not in expected["verdict_options"]:
            return False, f"Verdict '{actual_verdict}' not in {expected['verdict_options']}"
        return True, f"Verdict '{actual_verdict}' accepted, positions p1='{p1_pos}' p2='{p2_pos}'"

    return True, f"Positions p1='{p1_pos}' p2='{p2_pos}', same_position={result.get('same_position')}"


def evaluate_create(result, expected):
    # TC12: all-null input — must return data_warning (expected["data_warning"] is a non-null string)
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
            "result": result
        })

    total = len(test_cases)
    accuracy = passed / total
    print(f"\nAccuracy: {passed}/{total} = {accuracy:.2f} ({accuracy*100:.0f}%)")

    os.makedirs(Path(__file__).parent / "results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(__file__).parent / "results" / f"run_v3_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump({
            "version": "V3",
            "timestamp": timestamp,
            "accuracy": round(accuracy, 4),
            "passed": passed,
            "total": total,
            "results": results
        }, f, indent=2)
    print(f"Saved -> {out_path}")



if __name__ == "__main__":
    run_eval()
