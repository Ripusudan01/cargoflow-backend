from app.auth import get_current_user
from app.models import UserRole
from conftest import DummyUser
import pytest


# ---------------- ROLE OVERRIDE ----------------

def override_agent():
    return DummyUser(UserRole.DELIVERY_AGENT)


# ---------------- DASHBOARD ----------------

def test_dashboard(client):
    client.app.dependency_overrides[get_current_user] = override_agent
    res = client.get("/api/v1/agent/dashboard")
    assert res.status_code == 200


def test_dashboard_wrong_role(client):
    # default ADMIN
    res = client.get("/api/v1/agent/dashboard")
    assert res.status_code == 403


# ---------------- LOCATION ----------------

def test_update_location(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    res = client.post("/api/v1/agent/update/live-location", json={
        "lat": 10,
        "lng": 20
    })
    assert res.status_code == 200


def test_update_location_with_invalid_shipment(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    res = client.post("/api/v1/agent/update/live-location", json={
        "lat": 10,
        "lng": 20,
        "shipment_id": 999
    })
    assert res.status_code in [403, 404]


def test_update_location_missing_fields(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    res = client.post("/api/v1/agent/update/live-location", json={})
    assert res.status_code == 422


# ---------------- SHIPMENT STATUS ----------------

def test_update_shipment_status_invalid(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    res = client.patch("/api/v1/agent/shipments/999/status", json={
        "status": "DELIVERED"
    })
    assert res.status_code == 404


def test_update_shipment_status_wrong_role(client):
    # default ADMIN
    res = client.patch("/api/v1/agent/shipments/1/status", json={
        "status": "DELIVERED"
    })
    assert res.status_code == 403


# ---------------- DUTY STATUS ----------------

def test_update_duty_status(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    with pytest.raises(Exception):
        client.patch("/api/v1/agent/update/duty-status", json={
            "status": "ON_DUTY"
        })


def test_update_duty_status_invalid(client):
    client.app.dependency_overrides[get_current_user] = override_agent

    res = client.patch("/api/v1/agent/update/duty-status", json={})
    assert res.status_code == 422


def test_update_duty_status_wrong_role(client):
    res = client.patch("/api/v1/agent/update/duty-status", json={
        "status": "ON_DUTY"
    })
    assert res.status_code == 403