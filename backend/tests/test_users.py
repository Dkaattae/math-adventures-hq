def test_check_username_available(client):
    r = client.get("/api/users/check", params={"username": "Alice"})
    assert r.status_code == 200
    assert r.json() == {"username": "Alice", "available": True}


def test_check_username_taken_is_case_insensitive(client):
    client.post("/api/users", json={"username": "Alice", "pin": "1234"})
    r = client.get("/api/users/check", params={"username": "ALICE"})
    assert r.status_code == 200
    assert r.json()["available"] is False


def test_create_user(client):
    r = client.post("/api/users", json={"username": "Zoe", "pin": "1234"})
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "Zoe"
    assert "createdAt" in body
    # The PIN is never echoed back.
    assert "pin" not in body


def test_create_user_duplicate_returns_409(client):
    client.post("/api/users", json={"username": "Bob", "pin": "1234"})
    r = client.post("/api/users", json={"username": "Bob", "pin": "5678"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "username_taken"


def test_create_user_rejects_empty(client):
    r = client.post("/api/users", json={"username": "", "pin": "1234"})
    assert r.status_code == 422


def test_create_user_requires_4_digit_pin(client):
    assert client.post("/api/users", json={"username": "NoPin"}).status_code == 422
    assert client.post("/api/users", json={"username": "Short", "pin": "12"}).status_code == 422
    assert client.post("/api/users", json={"username": "Letters", "pin": "abcd"}).status_code == 422


def test_login_succeeds_with_correct_pin(client):
    client.post("/api/users", json={"username": "Mia", "pin": "4321"})
    r = client.post("/api/users/login", json={"username": "Mia", "pin": "4321"})
    assert r.status_code == 200
    assert r.json()["username"] == "Mia"


def test_login_is_case_insensitive_on_username(client):
    client.post("/api/users", json={"username": "Mia", "pin": "4321"})
    r = client.post("/api/users/login", json={"username": "MIA", "pin": "4321"})
    assert r.status_code == 200


def test_login_wrong_pin_returns_401(client):
    client.post("/api/users", json={"username": "Mia", "pin": "4321"})
    r = client.post("/api/users/login", json={"username": "Mia", "pin": "0000"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_login"


def test_login_unknown_user_returns_401(client):
    r = client.post("/api/users/login", json={"username": "Ghost", "pin": "1234"})
    assert r.status_code == 401


def test_pin_is_hashed_not_stored_plaintext(client, db_session):
    from app import storage

    client.post("/api/users", json={"username": "Secret", "pin": "1234"})
    row = storage.get_user_row(db_session, "Secret")
    assert row.pin_hash is not None
    assert "1234" not in row.pin_hash
    assert "$" in row.pin_hash  # salt$hash form
