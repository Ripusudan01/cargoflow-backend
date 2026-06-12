import uuid

import pytest

from app.database import SessionLocal
from app.models import (
    Address,
    AgentDutyStatus,
    Shipment,
    ShipmentStatus,
    User,
    UserRole,
)

# ---------------- DASHBOARD ----------------

def test_admin_dashboard(client):
    assert client.get("/api/v1/admin/dashboard").status_code == 200

def test_dashboard_shipments(client):
    assert client.get("/api/v1/admin/dashboard/shipments").status_code == 200

def test_dashboard_agents(client):
    assert client.get("/api/v1/admin/dashboard/agents").status_code == 200

def test_dashboard_clients(client):
    assert client.get("/api/v1/admin/dashboard/clients").status_code == 200


# ---------------- SHIPMENTS ----------------

def test_create_shipment_invalid_sender(client):
    res = client.post("/api/v1/admin/shipments", json={
        "sender_id": 999,
        "receiver_name": "R",
        "receiver_phone": "123",
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
    assert res.status_code == 404


def test_assign_agent_invalid(client):
    res = client.post("/api/v1/admin/shipments/999/assign/999")
    assert res.status_code == 404


def _create_assignment_case(status: ShipmentStatus):
    db = SessionLocal()
    try:
        suffix = uuid.uuid4()

        client_user = User(
            name="Client",
            email=f"client_{suffix}@test.com",
            phone="999",
            city="C",
            password_hash="test",
            role=UserRole.BUSINESS_CLIENT,
            is_active=True
        )
        initial_agent = User(
            name="Initial Agent",
            email=f"initial_agent_{suffix}@test.com",
            phone="999",
            city="C",
            password_hash="test",
            role=UserRole.DELIVERY_AGENT,
            is_active=True,
            duty_status=AgentDutyStatus.ON_DUTY
        )
        target_agent = User(
            name="Target Agent",
            email=f"target_agent_{suffix}@test.com",
            phone="999",
            city="C",
            password_hash="test",
            role=UserRole.DELIVERY_AGENT,
            is_active=True,
            duty_status=AgentDutyStatus.ON_DUTY
        )
        db.add_all([client_user, initial_agent, target_agent])
        db.flush()

        pickup = Address(
            line1="Pickup",
            city="C",
            state="S",
            pincode="1",
            latitude=0,
            longitude=0
        )
        delivery = Address(
            line1="Delivery",
            city="D",
            state="S",
            pincode="2",
            latitude=0,
            longitude=0
        )
        db.add_all([pickup, delivery])
        db.flush()

        shipment = Shipment(
            tracking_number=f"CF-TEST-{suffix}",
            sender_id=client_user.id,
            receiver_name="Receiver",
            receiver_phone="123",
            receiver_email="receiver@test.com",
            pickup_address_id=pickup.id,
            delivery_address_id=delivery.id,
            weight=1,
            price=10,
            status=status,
            assigned_agent_id=(
                initial_agent.id
                if status != ShipmentStatus.CREATED
                else None
            )
        )
        db.add(shipment)
        db.commit()

        return shipment.id, target_agent.id
    finally:
        db.close()


def _get_shipment(shipment_id: int):
    db = SessionLocal()
    try:
        return db.query(Shipment).filter(Shipment.id == shipment_id).first()
    finally:
        db.close()


def test_assign_created_shipment_success(client):
    shipment_id, target_agent_id = _create_assignment_case(ShipmentStatus.CREATED)

    res = client.post(f"/api/v1/admin/shipments/{shipment_id}/assign/{target_agent_id}")

    assert res.status_code == 200

    shipment = _get_shipment(shipment_id)
    assert shipment.status == ShipmentStatus.ASSIGNED
    assert shipment.assigned_agent_id == target_agent_id


@pytest.mark.parametrize("status", [
    ShipmentStatus.ASSIGNED,
    ShipmentStatus.OUT_FOR_DELIVERY,
    ShipmentStatus.DELIVERED,
    ShipmentStatus.FAILED,
])
def test_assign_non_created_shipment_returns_400(client, status):
    shipment_id, target_agent_id = _create_assignment_case(status)

    res = client.post(f"/api/v1/admin/shipments/{shipment_id}/assign/{target_agent_id}")

    assert res.status_code == 400
    assert res.json()["detail"] == f"Shipment cannot be assigned from status {status.value}"


# ---------------- DELIVERY AGENT ----------------

def test_add_delivery_agent(client):
    email = f"agent_{uuid.uuid4()}@test.com"

    res = client.post("/api/v1/admin/delivery_agents", json={
        "name": "A",
        "email": email,
        "phone": "999",
        "city": "C",
        "password": "123"
    })
    assert res.status_code == 201


def test_block_agent_not_found(client):
    res = client.patch("/api/v1/admin/delivery_agents/999/status")
    assert res.status_code == 404


def test_update_agent_not_found(client):
    res = client.patch("/api/v1/admin/delivery_agents/999", json={
        "name": "Updated"
    })
    assert res.status_code == 404


# ---------------- BUSINESS CLIENT ----------------

def test_add_business_client(client):
    email = f"client_{uuid.uuid4()}@test.com"

    res = client.post("/api/v1/admin/business_clients", json={
        "name": "Client",
        "email": email,
        "phone": "999",
        "city": "C",
        "password": "123"
    })
    assert res.status_code == 201


def test_block_client_not_found(client):
    res = client.patch("/api/v1/admin/business_clients/999/status")
    assert res.status_code == 404


def test_update_client_not_found(client):
    res = client.patch("/api/v1/admin/business_clients/999", json={
        "name": "Updated"
    })
    assert res.status_code == 404


# ---------------- LOCATION ----------------

def test_live_location(client):
    assert client.get("/api/v1/admin/agents/live-location").status_code == 200


# ---------------- VALIDATION ----------------

def test_missing_fields_delivery_agent(client):
    res = client.post("/api/v1/admin/delivery_agents", json={})
    assert res.status_code == 422
