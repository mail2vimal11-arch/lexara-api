"""Authentication routes — register, login, me."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.security import hash_password, verify_password, create_access_token
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "procurement"   # procurement | legal | admin


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        id=str(uuid.uuid4()),
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    log_action(db, "USER_REGISTERED", {"username": req.username, "role": req.role})
    return {"message": "User created", "username": req.username}


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login and receive a JWT access token."""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    log_action(db, "LOGIN", {"username": user.username}, user_id=user.id,
               ip_address=request.client.host if request.client else None)
    return {"access_token": token, "token_type": "bearer", "role": user.role}
