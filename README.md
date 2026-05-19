# Small Business Operations Platform (CargoFlow)

A scalable **FastAPI backend** for managing shipments, delivery agents, business clients, real-time tracking, and AI-powered chatbot support for logistics operations.

---

## Features

* JWT Authentication & Authorization
* Role-Based Access Control
* Shipment Management
* Delivery Agent Management
* Business Client Management
* Live Location Tracking for Agents
* Real-time Shipment Status Updates
* Public Shipment Tracking
* AI-powered RAG Chatbot with Knowledge Base Retrieval
* RESTful APIs with Swagger Documentation

---

## Tech Stack

* **Backend Framework:** FastAPI
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Authentication:** JWT Bearer Token
* **Package Manager:** uv
* **Testing:** Pytest
* **AI Integration:** Hugging Face API
* **Vector Embeddings:** Hugging Face Embeddings
* **AI Pipeline:** Retrieval-Augmented Generation (RAG)
* **Email Service:** Brevo API

---

# Project Setup

## 1. Clone Repository

```bash
git clone <your-repo-url>
cd backend
```

---

## 2. Create Virtual Environment

```bash
uv venv
```

### Activate Environment

#### Windows

```bash
.venv\Scripts\activate
```

#### Mac/Linux

```bash
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
uv sync
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root:

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

## 5. Run Development Server

```bash
uvicorn app.main:app --reload
```

---

## 6. API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 7. Run Tests

```bash
pytest -v
```

---

# Authentication

The backend uses **JWT Bearer Authentication**.

After login, include the token in all protected request headers:

```http
Authorization: Bearer <your_token>
```

---

# Roles & Permissions

| Role            | Permissions                                                           |
| --------------- | --------------------------------------------------------------------- |
| Admin           | Manage shipments, delivery agents, business clients     |
| Delivery Agent  | Update shipment status, update live location, request duty status     |
| Business Client | Create & track shipments, manage business profile                     |

---

# License

This project is developed for educational and business operations management purposes.
