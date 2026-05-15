# Small Business Operations Platform (CargoFlow) – Backend

This is the **FastAPI backend** for a Small Business Operations Platform that manages shipments, delivery agents and business clients.

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd backend
```

---

### 2. Create virtual environment (uv)

```bash
uv venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
uv sync
```

---

### 4. Configure Environment Variables

Create a ```.env``` file in the root directory:

```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/<db_name>

SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
ADMIN_PHONE=9999999999

HF_API_TOKEN=your_huggingface_token
BREVO_API_KEY=your_brevo_api_key
```

---

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

---

### 6. Access API docs

```
http://127.0.0.1:8000/docs
```

---

## 7. Running Tests

```bash
pytest -v
```

---

## Roles in System

| Role            | Permissions                        |
| --------------- | ---------------------------------- |
| Admin           | Manage shipments, agents, clients  |
| Delivery Agent  | Deliver shipments, update location |
| Business Client | Create & track shipments           |
