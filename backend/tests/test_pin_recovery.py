"""Rescue-code PIN recovery and brute-force lockout (PROJECT_PLAN §2.1)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app import storage

CODE_RE = re.compile(r"^[a-z]+-[a-z]+-\d{3}$")


def _signup(client, name="Kid", pin="1234"):
    r = client.post("/api/users", json={"username": name, "pin": pin})
    assert r.status_code == 201
    return r.json()


def test_signup_returns_a_rescue_code_once(client, db_session):
    body = _signup(client)
    code = body["recoveryCode"]
    assert CODE_RE.match(code), f"unexpected code format: {code}"

    # Only the hash is stored — the plaintext code appears nowhere in the DB.
    row = storage.get_user_row(db_session, "Kid")
    assert row.recovery_hash and code not in row.recovery_hash
    # Login/other responses never include it.
    login = client.post("/api/users/login", json={"username": "Kid", "pin": "1234"})
    assert "recoveryCode" not in login.json()


def test_reset_pin_with_rescue_code(client):
    code = _signup(client, pin="1111")["recoveryCode"]

    r = client.post(
        "/api/users/reset-pin",
        json={"username": "Kid", "recoveryCode": code, "newPin": "9876"},
    )
    assert r.status_code == 200

    # Old PIN dead, new PIN works.
    assert client.post("/api/users/login", json={"username": "Kid", "pin": "1111"}).status_code == 401
    assert client.post("/api/users/login", json={"username": "Kid", "pin": "9876"}).status_code == 200


def test_reset_pin_is_case_and_space_insensitive(client):
    code = _signup(client)["recoveryCode"]
    r = client.post(
        "/api/users/reset-pin",
        json={"username": "Kid", "recoveryCode": f"  {code.upper()}  ", "newPin": "2222"},
    )
    assert r.status_code == 200


def test_wrong_rescue_code_is_rejected(client):
    _signup(client)
    r = client.post(
        "/api/users/reset-pin",
        json={"username": "Kid", "recoveryCode": "red-tiger-000", "newPin": "2222"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_recovery_code"


def test_lockout_after_repeated_wrong_pins(client):
    _signup(client, pin="1234")
    for _ in range(storage.MAX_FAILED_ATTEMPTS):
        r = client.post("/api/users/login", json={"username": "Kid", "pin": "0000"})
    # The locking attempt itself returns 401; from now on it's 429...
    r = client.post("/api/users/login", json={"username": "Kid", "pin": "0000"})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "too_many_attempts"
    assert "Retry-After" in r.headers

    # ...even with the CORRECT pin, and for rescue-code resets too.
    assert client.post("/api/users/login", json={"username": "Kid", "pin": "1234"}).status_code == 429
    assert (
        client.post(
            "/api/users/reset-pin",
            json={"username": "Kid", "recoveryCode": "red-tiger-000", "newPin": "2222"},
        ).status_code
        == 429
    )


def test_wrong_rescue_codes_also_count_toward_lockout(client):
    _signup(client)
    for _ in range(storage.MAX_FAILED_ATTEMPTS):
        client.post(
            "/api/users/reset-pin",
            json={"username": "Kid", "recoveryCode": "red-tiger-000", "newPin": "2222"},
        )
    r = client.post("/api/users/login", json={"username": "Kid", "pin": "1234"})
    assert r.status_code == 429


def test_successful_login_resets_the_failure_counter(client):
    _signup(client, pin="1234")
    for _ in range(storage.MAX_FAILED_ATTEMPTS - 1):
        client.post("/api/users/login", json={"username": "Kid", "pin": "0000"})
    # One good login wipes the slate...
    assert client.post("/api/users/login", json={"username": "Kid", "pin": "1234"}).status_code == 200
    # ...so more wrong attempts start counting from zero (no lock yet).
    for _ in range(storage.MAX_FAILED_ATTEMPTS - 1):
        r = client.post("/api/users/login", json={"username": "Kid", "pin": "0000"})
    assert r.status_code == 401  # not 429


def test_lock_expires(client, db_session):
    _signup(client, pin="1234")
    for _ in range(storage.MAX_FAILED_ATTEMPTS):
        client.post("/api/users/login", json={"username": "Kid", "pin": "0000"})
    assert client.post("/api/users/login", json={"username": "Kid", "pin": "1234"}).status_code == 429

    # Time-travel the lock into the past.
    row = storage.get_user_row(db_session, "Kid")
    row.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    assert client.post("/api/users/login", json={"username": "Kid", "pin": "1234"}).status_code == 200


def test_unknown_user_login_is_401_not_429(client):
    for _ in range(storage.MAX_FAILED_ATTEMPTS + 2):
        r = client.post("/api/users/login", json={"username": "Ghost", "pin": "0000"})
    assert r.status_code == 401
