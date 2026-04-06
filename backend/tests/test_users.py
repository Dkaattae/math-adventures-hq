def test_check_username_available(client):
    r = client.get("/api/users/check", params={"username": "Alice"})
    assert r.status_code == 200
    assert r.json() == {"username": "Alice", "available": True}


def test_check_username_taken_is_case_insensitive(client):
    client.post("/api/users", json={"username": "Alice"})
    r = client.get("/api/users/check", params={"username": "ALICE"})
    assert r.status_code == 200
    assert r.json()["available"] is False


def test_create_user(client):
    r = client.post("/api/users", json={"username": "Zoe"})
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "Zoe"
    assert "createdAt" in body


def test_create_user_duplicate_returns_409(client):
    client.post("/api/users", json={"username": "Bob"})
    r = client.post("/api/users", json={"username": "Bob"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "username_taken"


def test_create_user_rejects_empty(client):
    r = client.post("/api/users", json={"username": ""})
    assert r.status_code == 422
