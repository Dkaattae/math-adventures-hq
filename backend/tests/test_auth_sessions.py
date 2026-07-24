"""Session tokens gating the per-player endpoints (PROJECT_PLAN §2.1)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import storage
from app.db_models import SessionRow

PROTECTED = ["/api/users/Ada/stats", "/api/users/Ada/suggested-level"]


def _token(client, username="Ada", pin="1234") -> str:
    return client.post("/api/users", json={"username": username, "pin": pin}).json()["token"]


def test_signup_login_and_reset_all_issue_tokens(client):
    created = client.post("/api/users", json={"username": "Ada", "pin": "1234"}).json()
    assert created["token"]

    logged_in = client.post("/api/users/login", json={"username": "Ada", "pin": "1234"}).json()
    assert logged_in["token"] and logged_in["token"] != created["token"]

    reset = client.post(
        "/api/users/reset-pin",
        json={"username": "Ada", "recoveryCode": created["recoveryCode"], "newPin": "9999"},
    ).json()
    assert reset["token"]


def test_protected_endpoints_reject_anonymous_requests(client):
    _token(client)
    for path in PROTECTED:
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.json()["detail"]["code"] == "unauthorized"


def test_protected_endpoints_accept_own_token(client):
    token = _token(client)
    for path in PROTECTED:
        r = client.get(path, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, path


def test_another_players_token_cannot_read_your_stats(client):
    _token(client, "Ada")
    nosy = _token(client, "Nosy")
    for path in PROTECTED:
        r = client.get(path, headers={"Authorization": f"Bearer {nosy}"})
        assert r.status_code == 401, path


def test_token_owner_check_is_case_insensitive(client):
    token = _token(client, "Ada")
    r = client.get("/api/users/ADA/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_garbage_and_malformed_tokens_are_rejected(client):
    _token(client)
    for header in ["Bearer not-a-real-token", "Basic abc123", "Bearer", "justastring"]:
        r = client.get("/api/users/Ada/stats", headers={"Authorization": header})
        assert r.status_code == 401, header


def test_expired_token_stops_working(client, db_session):
    token = _token(client)
    row = db_session.get(SessionRow, storage._hash_token(token))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    r = client.get("/api/users/Ada/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    # The expired row is cleaned up on the way past.
    assert db_session.get(SessionRow, storage._hash_token(token)) is None


def test_pin_reset_revokes_existing_sessions(client):
    created = client.post("/api/users", json={"username": "Ada", "pin": "1234"}).json()
    old = {"Authorization": f"Bearer {created['token']}"}
    assert client.get("/api/users/Ada/stats", headers=old).status_code == 200

    fresh = client.post(
        "/api/users/reset-pin",
        json={"username": "Ada", "recoveryCode": created["recoveryCode"], "newPin": "5555"},
    ).json()

    # Whoever held the old token (that's the point of a reset) is out.
    assert client.get("/api/users/Ada/stats", headers=old).status_code == 401
    assert client.get(
        "/api/users/Ada/stats", headers={"Authorization": f"Bearer {fresh['token']}"}
    ).status_code == 200


def test_tokens_are_stored_hashed(client, db_session):
    token = _token(client)
    rows = db_session.query(SessionRow).all()
    assert len(rows) == 1
    assert token not in rows[0].token_hash
    assert len(rows[0].token_hash) == 64  # sha256 hex


def test_leaderboard_stays_public(client):
    """Only per-player history moved behind auth."""
    assert client.get("/api/leaderboard").status_code == 200
