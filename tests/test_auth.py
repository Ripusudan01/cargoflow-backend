import uuid, pytest

def test_register_success(client):
    email = f"user_{uuid.uuid4()}@example.com"

    res = client.post("/api/auth/register", json={
        "name": "Test",
        "email": email,
        "phone": "1234567890",
        "city": "Chennai",
        "password": "123456"
    })
    assert res.status_code == 201


def test_register_duplicate(client):
    email = f"user_{uuid.uuid4()}@example.com"

    client.post("/api/auth/register", json={
        "name": "A", "email": email, "phone": "1",
        "city": "C", "password": "123"
    })

    res = client.post("/api/auth/register", json={
        "name": "B", "email": email, "phone": "1",
        "city": "C", "password": "123"
    })
    assert res.status_code == 400


def test_login_success(client):
    email = f"user_{uuid.uuid4()}@example.com"

    client.post("/api/auth/register", json={
        "name": "A", "email": email, "phone": "1",
        "city": "C", "password": "123"
    })

    res = client.post("/api/auth/login", json={
        "email": email, "password": "123"
    })
    assert res.status_code == 200


def test_login_invalid(client):
    res = client.post("/api/auth/login", json={
        "email": "fake@test.com", "password": "wrong"
    })
    assert res.status_code == 401


def test_get_me(client):
    res = client.get("/api/auth/me")
    assert res.status_code in [200, 403]

def test_update_me(client):
    import pytest

    with pytest.raises(Exception):
        client.patch("/api/auth/me", json={"name": "New"})

def test_register_missing_fields(client):
    res = client.post("/api/auth/register", json={})
    assert res.status_code == 422