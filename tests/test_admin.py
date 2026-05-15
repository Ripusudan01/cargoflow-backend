import uuid

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