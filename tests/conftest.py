import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user
from app.models import UserRole
from app.utils import email


# ---------------- DUMMY USER ----------------

class DummyUser:
    def __init__(self, role):
        self.id = 1
        self.name = "Test User"
        self.email = "test@example.com"
        self.phone = "1234567890"
        self.role = role
        self.is_active = True
        self.business = None
        self.owned_business = None


# ---------------- CLIENT FIXTURE ----------------

@pytest.fixture
def client():
    def override_admin():
        return DummyUser(UserRole.ADMIN)

    app.dependency_overrides[get_current_user] = override_admin

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    def fake_send_email(*args, **kwargs):
        return True
    monkeypatch.setattr(email, "send_email", fake_send_email)