from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ---------- PASSWORD ----------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT ----------
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------- CURRENT USER ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == payload["sub"]).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ---------- ROLE CHECK ----------
def require_role(*required_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)):
        if not current_user.is_active:
            raise HTTPException(status_code=403,
                                detail="Account is blocked")

        if current_user.role not in required_roles:
            raise HTTPException(status_code=403,
                                detail="Access denied: insufficient role")
        return current_user
    return role_checker