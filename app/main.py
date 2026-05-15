from fastapi import FastAPI
from dotenv import load_dotenv
import os

from .database import Base, engine, SessionLocal
from .models import User, UserRole
from .routes import auth_routes, admin_routes, client_routes, agent_routes
from .auth import hash_password

from chatbot.app import router as chatbot_router
import chatbot.app as chatbot_module
from chatbot.rag_pipeline import CargoFlowRAG


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
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        if not admin:
            new_admin = User(
                name="Admin",
                email=os.getenv("ADMIN_EMAIL"),
                password_hash=hash_password(os.getenv("ADMIN_PASSWORD")),
                phone=os.getenv("ADMIN_PHONE"),
                role=UserRole.ADMIN,
                is_active=True)
            db.add(new_admin)
            db.commit()

    finally:
        db.close()

    chatbot_module.rag = CargoFlowRAG()

@app.get("/health")
def health():
    return {"status": "API working"}
