"""Authentication routes — register, login, me."""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.security import hash_password, verify_password, create_access_token
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _500_with_cause(e: Exception) -> HTTPException:
    """TEMPORARY (live incident 2026-09-05): surface the exception class in
    the 500 detail. Unhandled exceptions bypass CORSMiddleware, so browsers
    report them as CORS/"Load failed" and hide the real failure. Class names
    only — no messages, no values. Remove once registration is confirmed
    working in production."""
    logger.exception("auth route failed")
    orig = getattr(e, "orig", None)
    cause = type(e).__name__ + (f":{type(orig).__name__}" if orig is not None else "")
    return HTTPException(status_code=500, detail=f"auth_failed:{cause}")


@router.post("/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""  # CA-026: made async (consistent with all v1 endpoints)
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    try:
        user = User(
            id=str(uuid.uuid4()),
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password),
            role="procurement",
        )
        db.add(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _500_with_cause(e)
    log_action(db, "USER_REGISTERED", {"username": req.username, "role": "procurement"})
    return {"message": "User created", "username": req.username}


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login and receive a JWT access token."""
    try:
        user = db.query(User).filter(User.username == req.username).first()
    except Exception as e:
        db.rollback()
        raise _500_with_cause(e)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    log_action(db, "LOGIN", {"username": user.username}, user_id=user.id,
               ip_address=request.client.host if request.client else None)
    return {"access_token": token, "token_type": "bearer", "role": user.role}
