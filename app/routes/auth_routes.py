from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, UserRole
from ..schemas import UserRegister, UserLogin, UserUpdate
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from app.utils.email import send_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", status_code=201)
def register_user(data: UserRegister,
                  background_tasks: BackgroundTasks,
                  db: Session = Depends(get_db)):
    
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = UserRole.BUSINESS_CLIENT
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        city=data.city,
        password_hash=hash_password(data.password),
        role=role)

    db.add(user)
    db.commit()
    db.refresh(user)

    html_content = f"""
        <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7fa; padding: 50px 20px; line-height: 1.6;">
    <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
        
        <div style="background-color: #0f172a; padding: 40px 30px; text-align: center; border-bottom: 4px solid #2563eb;">
            <span style="color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; text-transform: none;">
                Cargo<span style="color: #2563eb;">Flow</span>
            </span>
            <p style="color: #94a3b8; font-size: 12px; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px;">Smart Logistics for SMEs</p>
        </div>

        <div style="padding: 50px 40px;">
            <h2 style="color: #1e293b; margin-top: 0; font-size: 26px; font-weight: 700;">Welcome to the fleet, {user.name}!</h2>
            <p style="color: #64748b; font-size: 16px; margin-bottom: 30px;">
                Your registration is complete. You now have full access to our shipment management suite. We’re excited to help you streamline your operations.
            </p>

            <div style="background: #f8fafc; border-left: 4px solid #2563eb; padding: 25px; border-radius: 4px; margin: 30px 0;">
                <table width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                        <td style="color: #475569; font-size: 14px; padding-bottom: 8px;"><strong>Account Email</strong></td>
                    </tr>
                    <tr>
                        <td style="color: #1e293b; font-size: 16px; font-weight: 600;">{user.email}</td>
                    </tr>
                    <tr>
                        <td style="padding-top: 15px;">
                            <span style="background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase;">
                                Active Account
                            </span>
                        </td>
                    </tr>
                </table>
            </div>

            <div style="text-align: center; margin-top: 40px;">
                <a href="http://localhost:5173/login" style="background-color: #2563eb; color: #ffffff; padding: 18px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px; display: inline-block; box-shadow: 0 4px 14px rgba(58, 97, 171, 0.3);">
                    Go to Dashboard
                </a>
            </div>
        </div>

        <div style="background-color: #f1f5f9; padding: 25px; text-align: center; border-top: 1px solid #e2e8f0;">
            <table width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td align="center" style="width: 33%;">
                        <div style="font-weight: 800; color: #1e293b; font-size: 18px;">99.8%</div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Uptime</div>
                    </td>
                    <td align="center" style="width: 33%; border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1;">
                        <div style="font-weight: 800; color: #1e293b; font-size: 18px;">250K+</div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Delivered</div>
                    </td>
                    <td align="center" style="width: 33%;">
                        <div style="font-weight: 800; color: #1e293b; font-size: 18px;">24/7</div>
                        <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Support</div>
                    </td>
                </tr>
            </table>
        </div>

        <div style="padding: 30px; text-align: center; background-color: #0f172a;">
            <p style="font-size: 12px; color: #64748b; margin: 0;">
                © 2026 CargoFlow Inc. All rights reserved.
            </p>
            <p style="font-size: 11px; color: #475569; margin-top: 10px;">
                You received this because you signed up for a CargoFlow account.
            </p>
        </div>
    </div>
    </div>
    """

    try:
        background_tasks.add_task(
            send_email,
            user.email,
            "Welcome to CargoFlow",
            html_content
        )
    except Exception as e:
        print("Email scheduling failed:", str(e))

    return {
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value
        }
    }

@router.post("/login", status_code=200)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is blocked")

    token = create_access_token({"sub": user.email, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value
    }

@router.get("/me", status_code=200)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role.value
    }

@router.patch("/me", status_code=200)
def update_me(data: UserUpdate, 
              db: Session = Depends(get_db), 
              current_user: User = Depends(get_current_user)):

    if data.name is not None:
        current_user.name = data.name

    if data.email is not None:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already in use")
        else:
            current_user.email = data.email

    if data.phone is not None:
        current_user.phone = data.phone
    
    if data.password is not None:
        current_user.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
            "role": current_user.role.value
        }
    }