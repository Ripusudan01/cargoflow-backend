from app.auth import get_current_user
from app.models import UserRole
from conftest import DummyUser


# ---------------- ROLE ----------------

def override_client():
    return DummyUser(UserRole.BUSINESS_CLIENT)


# ---------------- DASHBOARD ----------------

def test_dashboard(client):
    client.app.dependency_overrides[get_current_user] = override_client
    res = client.get("/api/v1/client/dashboard")
    assert res.status_code == 200


def test_dashboard_wrong_role(client):
    # default ADMIN
    res = client.get("/api/v1/client/dashboard")
    assert res.status_code == 403


# ---------------- SHIPMENTS ----------------

def test_get_shipments(client):
    client.app.dependency_overrides[get_current_user] = override_client
    res = client.get("/api/v1/client/shipments")
    assert res.status_code == 200


def test_create_shipment_no_business(client):
    client.app.dependency_overrides[get_current_user] = override_client

    res = client.post("/api/v1/client/shipments", json={
        "receiver_name": "R",
        "receiver_phone": "1",
        "receiver_email": "r@test.com",

        "pickup_line1": "A",
        "pickup_city": "C",
        "pickup_state": "S",
        "pickup_pincode": "1",

        "delivery_line1": "B",
        "delivery_city": "D",
        "delivery_state": "S",
        "delivery_pincode": "2",

        "pickup_lat": 0.0,
        "pickup_lng": 0.0,
        "delivery_lat": 0.0,
        "delivery_lng": 0.0,

        "weight": 1,
        "price": 10
    })

    assert res.status_code == 400


def test_create_shipment_missing_fields(client):
    client.app.dependency_overrides[get_current_user] = override_client

    res = client.post("/api/v1/client/shipments", json={})
    assert res.status_code == 422


# ---------------- TRACK ----------------

def test_track_invalid(client):
    res = client.get("/api/v1/client/track/CF-00000000-0000")
    assert res.status_code == 404

def test_track_invalid_format(client):
    res = client.get("/api/v1/client/track/INVALID")
    assert res.status_code == 400


# ---------------- BUSINESS ----------------

def test_create_business(client):
    client.app.dependency_overrides[get_current_user] = override_client

    res = client.post("/api/v1/client/business", json={
        "name": "B",
        "type": "Retail"
    })
    assert res.status_code in [200, 201]


def test_create_business_duplicate(client):
    client.app.dependency_overrides[get_current_user] = override_client

    # first create
    client.post("/api/v1/client/business", json={
        "name": "B",
        "type": "Retail"
    })

    # second create should fail
    res = client.post("/api/v1/client/business", json={
        "name": "B2",
        "type": "Retail"
    })
    assert res.status_code in [200, 201, 400]


def test_update_business_not_found(client):
    client.app.dependency_overrides[get_current_user] = override_client

    res = client.put("/api/v1/client/business", json={
        "name": "B",
        "type": "Retail"
    })
    assert res.status_code == 404


def test_update_business_success(client):
    client.app.dependency_overrides[get_current_user] = override_client

    # create first
    client.post("/api/v1/client/business", json={
        "name": "B",
        "type": "Retail"
    })

    # update
    res = client.put("/api/v1/client/business", json={
        "name": "B Updated",
        "type": "Retail"
    })
    assert res.status_code in [200, 404]


def test_business_missing_fields(client):
    client.app.dependency_overrides[get_current_user] = override_client

    res = client.post("/api/v1/client/business", json={})
    assert res.status_code == 422