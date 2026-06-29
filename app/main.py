from fastapi import FastAPI
from dotenv import load_dotenv
import os

from .database import Base, engine, SessionLocal
from .models import User, UserRole
from .routes import auth_routes, admin_routes, client_routes, agent_routes
from .auth import hash_password
from .settings import require_env

from chatbot.app import router as chatbot_router


from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://cargo-flow-ppt.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(client_routes.router)
app.include_router(agent_routes.router)

app.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        admin_email = require_env("ADMIN_EMAIL")
        admin_password = require_env("ADMIN_PASSWORD")
        admin_phone = require_env("ADMIN_PHONE")

        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        if not admin:
            new_admin = User(
                name="Admin",
                email=admin_email,
                password_hash=hash_password(admin_password),
                phone=admin_phone,
                role=UserRole.ADMIN,
                is_active=True)
            db.add(new_admin)
            db.commit()

    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "API working"}
