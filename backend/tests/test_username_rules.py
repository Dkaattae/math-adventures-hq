"""Username charset + signup rate limiting (PROJECT_PLAN §2.2)."""
from __future__ import annotations

import pytest

from app.ratelimit import SlidingWindowLimiter, signup_limiter

GOOD = ["Ada", "anna-lee", "O'Neil", "kid_7", "Mia Rose", "José", "12", "x"]
BAD = [
    "",                      # empty
    " ",                     # whitespace only
    "_leading",              # must start with a letter or digit
    "-nope",
    "bad<script>",           # markup
    "semi;colon",
    "new\nline",
    "emoji🎉",
    "slash/name",
    "quote\"name",
    "a" * 21,                # too long
]


@pytest.mark.parametrize("username", GOOD)
def test_accepts_kid_friendly_names(client, username):
    r = client.post("/api/users", json={"username": username, "pin": "1234"})
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("username", BAD)
def test_rejects_junk_names(client, username):
    r = client.post("/api/users", json={"username": username, "pin": "1234"})
    assert r.status_code == 422, f"{username!r} should have been rejected"


def test_surrounding_whitespace_is_trimmed_not_rejected(client):
    r = client.post("/api/users", json={"username": "  Ada  ", "pin": "1234"})
    assert r.status_code == 201
    assert r.json()["username"] == "Ada"


def test_login_and_reset_apply_the_same_charset(client):
    assert client.post(
        "/api/users/login", json={"username": "bad<script>", "pin": "1234"}
    ).status_code == 422
    assert client.post(
        "/api/users/reset-pin",
        json={"username": "bad<script>", "recoveryCode": "gold-otter-731", "newPin": "1234"},
    ).status_code == 422


def test_quiz_creation_applies_the_same_charset(client):
    r = client.post(
        "/api/quizzes",
        json={
            "username": "bad<script>",
            "grade": "1",
            "mathType": "addition",
            "difficulty": "easy",
        },
    )
    assert r.status_code == 422


def test_availability_check_rejects_junk(client):
    assert client.get("/api/users/check", params={"username": "bad<script>"}).status_code == 422


# ---------- signup rate limiting ----------


def test_signup_is_rate_limited_per_client(client, monkeypatch):
    monkeypatch.setattr(signup_limiter, "limit", 3)

    for i in range(3):
        assert client.post("/api/users", json={"username": f"Kid{i}", "pin": "1234"}).status_code == 201

    r = client.post("/api/users", json={"username": "OneTooMany", "pin": "1234"})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "too_many_signups"
    assert int(r.headers["Retry-After"]) > 0
    # The blocked name is still free afterwards — nothing was created.
    assert client.get("/api/users/check", params={"username": "OneTooMany"}).json()["available"]


def test_failed_signups_count_toward_the_limit(client, monkeypatch):
    """Otherwise hammering one taken name is a free pass."""
    monkeypatch.setattr(signup_limiter, "limit", 3)
    assert client.post("/api/users", json={"username": "Taken", "pin": "1234"}).status_code == 201
    assert client.post("/api/users", json={"username": "Taken", "pin": "1234"}).status_code == 409
    assert client.post("/api/users", json={"username": "Taken", "pin": "1234"}).status_code == 409
    assert client.post("/api/users", json={"username": "Fresh", "pin": "1234"}).status_code == 429


def test_login_is_not_rate_limited_by_the_signup_limiter(client, monkeypatch):
    """Returning players share the family IP; only signup is throttled."""
    monkeypatch.setattr(signup_limiter, "limit", 1)
    client.post("/api/users", json={"username": "Ada", "pin": "1234"})
    for _ in range(5):
        assert client.post(
            "/api/users/login", json={"username": "Ada", "pin": "1234"}
        ).status_code == 200


def test_separate_client_ips_get_separate_budgets(client, monkeypatch):
    monkeypatch.setattr(signup_limiter, "limit", 1)
    assert client.post(
        "/api/users", json={"username": "Home", "pin": "1234"},
        headers={"X-Forwarded-For": "10.0.0.1"},
    ).status_code == 201
    assert client.post(
        "/api/users", json={"username": "Blocked", "pin": "1234"},
        headers={"X-Forwarded-For": "10.0.0.1"},
    ).status_code == 429
    assert client.post(
        "/api/users", json={"username": "School", "pin": "1234"},
        headers={"X-Forwarded-For": "10.0.0.2"},
    ).status_code == 201


# ---------- the limiter itself ----------


def test_limiter_window_slides():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.hit("ip") is None
    assert limiter.hit("ip") is None
    retry_after = limiter.hit("ip")
    assert retry_after is not None and 0 < retry_after <= 61

    # Pretend the recorded hits are older than the window.
    limiter._hits["ip"] = type(limiter._hits["ip"])(t - 61 for t in limiter._hits["ip"])
    assert limiter.hit("ip") is None


def test_limiter_of_zero_is_disabled():
    limiter = SlidingWindowLimiter(limit=0, window_seconds=60)
    for _ in range(50):
        assert limiter.hit("ip") is None
