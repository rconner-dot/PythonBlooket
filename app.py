"""PyBlooket web server.

Run with ``python app.py`` and open http://127.0.0.1:5000
"""

from __future__ import annotations

import os
import random
import threading
import uuid
from collections import OrderedDict

from flask import Flask, jsonify, request, send_from_directory

from pyblooket.questions import (
    DIFFICULTIES,
    DIFFICULTY_LABELS,
    DIFFICULTY_POINTS,
    TOPICS,
    GenerationError,
    Question,
    available_topics,
    generate_question,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_PENDING = 20_000
MAX_BATCH = 20

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")


class PendingQuestions:
    """Server-side answer store, so the client never sees the answer early.

    Bounded LRU: the oldest unanswered questions are forgotten first.
    """

    def __init__(self, limit: int = MAX_PENDING):
        self._items: OrderedDict[str, Question] = OrderedDict()
        self._lock = threading.Lock()
        self._limit = limit

    def add(self, q: Question) -> str:
        qid = uuid.uuid4().hex
        with self._lock:
            self._items[qid] = q
            while len(self._items) > self._limit:
                self._items.popitem(last=False)
        return qid

    def pop(self, qid: str) -> Question | None:
        with self._lock:
            return self._items.pop(qid, None)


pending = PendingQuestions()


def _parse_topics(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t for t in raw.split(",") if t in TOPICS]


def _parse_difficulty(raw: str | None) -> int | None:
    if raw in (None, "", "mixed"):
        return None
    try:
        d = int(raw)
    except ValueError:
        return None
    return d if d in DIFFICULTIES else None


def _question_payload(q: Question) -> dict:
    data = q.public_dict()
    data["id"] = pending.add(q)
    data["topic_name"], data["topic_icon"], _ = TOPICS[q.topic]
    return data


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/topics")
def api_topics():
    return jsonify(
        {
            "topics": available_topics(),
            "difficulties": [
                {"id": d, "label": DIFFICULTY_LABELS[d], "points": DIFFICULTY_POINTS[d]}
                for d in DIFFICULTIES
            ],
        }
    )


@app.get("/api/questions")
def api_questions():
    """GET /api/questions?topics=a,b&difficulty=1|2|3|mixed&count=N"""
    topics = _parse_topics(request.args.get("topics"))
    difficulty = _parse_difficulty(request.args.get("difficulty"))
    try:
        count = max(1, min(MAX_BATCH, int(request.args.get("count", 1))))
    except ValueError:
        count = 1
    rng = random.Random()
    try:
        qs = [generate_question(topics, difficulty, rng) for _ in range(count)]
    except GenerationError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"questions": [_question_payload(q) for q in qs]})


@app.post("/api/answer")
def api_answer():
    """POST {"id": "...", "choice": <index or null if timed out>}"""
    body = request.get_json(silent=True) or {}
    q = pending.pop(str(body.get("id", "")))
    if q is None:
        return jsonify({"error": "unknown or already-answered question"}), 404
    choice = body.get("choice")
    correct = isinstance(choice, int) and not isinstance(choice, bool) and choice == q.answer
    return jsonify(
        {
            "correct": correct,
            "answer": q.answer,
            "points": q.points if correct else 0,
            "explanation": q.explanation,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, debug=False, threaded=True)
