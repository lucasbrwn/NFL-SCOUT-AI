from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, static_folder="static")

from ai import grader, compare, create_player

VALID_POSITIONS = ["QB", "RB", "WR", "TE", "OL", "DE", "DT", "LB", "CB", "S"]
STAT_FIELDS = ["forty_yard", "bench_reps", "vertical_jump", "broad_jump",
               "three_cone", "shuttle", "height_in", "weight_lbs"]


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/grade", methods=["POST"])
def api_grade():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    position = (body.get("position") or "").strip() or None
    try:
        result = grader.grade_player(name, position)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/compare", methods=["POST"])
def api_compare():
    body = request.get_json(silent=True) or {}
    name1 = body.get("name1", "").strip()
    name2 = body.get("name2", "").strip()
    if not name1:
        return jsonify({"ok": False, "error": "name1 is required"}), 400
    if not name2:
        return jsonify({"ok": False, "error": "name2 is required"}), 400
    position1 = (body.get("position1") or "").strip() or None
    position2 = (body.get("position2") or "").strip() or None
    try:
        result = compare.compare_players(name1, name2, position1, position2)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/create", methods=["POST"])
def api_create():
    body = request.get_json(silent=True) or {}
    position = body.get("position", "").strip()
    if position not in VALID_POSITIONS:
        return jsonify({"ok": False, "error": f"position must be one of {VALID_POSITIONS}"}), 400

    stats = {field: body.get(field) for field in STAT_FIELDS}
    if not any(v is not None for v in stats.values()):
        return jsonify({"ok": False, "error": "at least one combine stat is required"}), 400

    try:
        result = create_player.create_player(position, **stats)
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
