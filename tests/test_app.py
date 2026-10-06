from __future__ import annotations

import pytest

from app import app
from pyblooket.questions import TOPICS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"<html" in res.data.lower()


def test_topics_endpoint(client):
    data = client.get("/api/topics").get_json()
    ids = {t["id"] for t in data["topics"]}
    assert ids == set(TOPICS)
    assert [d["points"] for d in data["difficulties"]] == [100, 250, 500]


def test_question_does_not_leak_answer(client):
    data = client.get("/api/questions?count=5").get_json()
    assert len(data["questions"]) == 5
    for q in data["questions"]:
        assert "answer" not in q and "explanation" not in q
        assert len(q["choices"]) == 4


@pytest.mark.parametrize("difficulty,points", [(1, 100), (2, 250), (3, 500)])
def test_difficulty_filter_and_points(client, difficulty, points):
    data = client.get(f"/api/questions?difficulty={difficulty}&count=10").get_json()
    for q in data["questions"]:
        assert q["difficulty"] == difficulty
        assert q["points"] == points


def test_topic_filter(client):
    data = client.get("/api/questions?topics=strings,loops&count=20").get_json()
    assert {q["topic"] for q in data["questions"]} <= {"strings", "loops"}


def test_answer_flow(client):
    q = client.get("/api/questions").get_json()["questions"][0]
    first = client.post("/api/answer", json={"id": q["id"], "choice": 0}).get_json()
    assert set(first) == {"correct", "answer", "points", "explanation"}
    assert first["correct"] == (first["answer"] == 0)
    assert first["points"] == (q["points"] if first["correct"] else 0)
    # A question can only be answered once.
    again = client.post("/api/answer", json={"id": q["id"], "choice": first["answer"]})
    assert again.status_code == 404


def test_timeout_answer_is_wrong(client):
    q = client.get("/api/questions").get_json()["questions"][0]
    res = client.post("/api/answer", json={"id": q["id"], "choice": None}).get_json()
    assert res["correct"] is False and res["points"] == 0


def test_unknown_question(client):
    assert client.post("/api/answer", json={"id": "nope", "choice": 1}).status_code == 404
