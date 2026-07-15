from uuid import UUID

from app import storage


def _make_user(client, name="Alice"):
    client.post("/api/users", json={"username": name, "pin": "1234"})
    return name


def _new_quiz(client, **overrides):
    name = overrides.pop("username", _make_user(client))
    payload = {
        "username": name,
        "grade": "3",
        "mathType": "addition",
        "difficulty": "easy",
    }
    payload.update(overrides)
    return client.post("/api/quizzes", json=payload)


def test_create_quiz_returns_10_questions_without_answers(client):
    r = _new_quiz(client)
    assert r.status_code == 201
    body = r.json()
    assert len(body["questions"]) == 10
    for q in body["questions"]:
        # No answer key leaks; typed quizzes carry no options.
        assert "correctAnswer" not in q
        assert "explanation" not in q
        assert q["options"] is None
    assert [q["id"] for q in body["questions"]] == list(range(10))


def test_create_quiz_unknown_user_404(client):
    r = _new_quiz(client, username="Ghost")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "user_not_found"


def test_get_quiz_roundtrip(client):
    created = _new_quiz(client).json()
    r = client.get(f"/api/quizzes/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_quiz_not_found(client):
    r = client.get("/api/quizzes/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_submit_all_correct_returns_perfect_score(client, db_session):
    created = _new_quiz(client).json()
    row = storage.get_quiz(db_session, UUID(created["id"]))
    answers = [str(q.correctAnswer) for q in storage.quiz_questions(row)]
    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": answers, "timeUsedSeconds": 90},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 10
    assert body["total"] == 10
    assert body["badge"] == "🏆"
    assert all(item["isCorrect"] for item in body["results"])


def test_submit_all_wrong_returns_zero(client):
    created = _new_quiz(client).json()
    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": ["nope"] * 10, "timeUsedSeconds": 200},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 0
    assert body["badge"] is None
    assert all(item["isCorrect"] is False for item in body["results"])


def test_submit_null_answers_are_wrong(client):
    created = _new_quiz(client).json()
    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": [None] * 10, "timeUsedSeconds": 0},
    )
    assert r.status_code == 200
    assert r.json()["score"] == 0


def test_submit_twice_conflicts(client):
    created = _new_quiz(client).json()
    payload = {"answers": [None] * 10, "timeUsedSeconds": 10}
    client.post(f"/api/quizzes/{created['id']}/submit", json=payload)
    r = client.post(f"/api/quizzes/{created['id']}/submit", json=payload)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "already_submitted"


def test_submit_wrong_length_422(client):
    created = _new_quiz(client).json()
    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": ["1"] * 5, "timeUsedSeconds": 10},
    )
    assert r.status_code == 422


def test_submit_unknown_quiz_404(client):
    r = client.post(
        "/api/quizzes/00000000-0000-0000-0000-000000000000/submit",
        json={"answers": [None] * 10, "timeUsedSeconds": 10},
    )
    assert r.status_code == 404


def test_submit_clamps_reported_time_to_server_window(client, db_session):
    """A client claiming more time than actually elapsed gets clamped."""
    created = _new_quiz(client).json()
    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": [None] * 10, "timeUsedSeconds": 9999},
    )
    assert r.status_code == 200
    # The quiz was created moments ago, so the observed window is ~0-2s.
    assert r.json()["timeUsedSeconds"] <= 5

    # The leaderboard entry records the clamped value too.
    board = client.get("/api/leaderboard").json()
    assert all(e["timeUsedSeconds"] <= 5 for e in board)


def test_submit_keeps_honest_reported_time(client, db_session):
    """A reported time within the observed window passes through unchanged."""
    from datetime import timedelta

    created = _new_quiz(client).json()
    row = storage.get_quiz(db_session, UUID(created["id"]))
    row.created_at = row.created_at - timedelta(seconds=120)
    db_session.commit()

    r = client.post(
        f"/api/quizzes/{created['id']}/submit",
        json={"answers": [None] * 10, "timeUsedSeconds": 90},
    )
    assert r.status_code == 200
    assert r.json()["timeUsedSeconds"] == 90


def test_datetimes_are_timezone_aware_even_on_sqlite(client, db_session):
    """UTCDateTime must re-attach tzinfo that sqlite drops (plan bug: naive
    datetimes broke aware arithmetic and made API timestamps ambiguous)."""
    created = _new_quiz(client).json()
    # Force a round-trip through the database rather than reading the
    # cached Python object.
    db_session.expire_all()
    row = storage.get_quiz(db_session, UUID(created["id"]))
    assert row.created_at.tzinfo is not None

    # API timestamps carry an explicit UTC offset.
    assert created["createdAt"].endswith("+00:00") or created["createdAt"].endswith("Z")
