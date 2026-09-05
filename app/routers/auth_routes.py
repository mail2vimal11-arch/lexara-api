"""Authentication routes — register, login, me, password reset."""

import hashlib
import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models.user import User
from app.security import hash_password, verify_password, create_access_token, decode_token
from app.services.audit_service import log_action
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _auth_500(e: Exception) -> HTTPException:
    """Convert an unexpected failure into an HTTPException so the response
    goes through the normal handlers and keeps its CORS headers — a raw
    unhandled exception bypasses CORSMiddleware and browsers report it as a
    CORS failure instead of a server error (the QA-BUG-5 incident)."""
    logger.exception("auth route failed")
    return HTTPException(status_code=500, detail="Something went wrong. Please try again later.")


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
        raise _auth_500(e)
    log_action(db, "USER_REGISTERED", {"username": req.username, "role": "procurement"})
    return {"message": "User created", "username": req.username}


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login and receive a JWT access token."""
    try:
        user = db.query(User).filter(User.username == req.username).first()
    except Exception as e:
        db.rollback()
        raise _auth_500(e)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    log_action(db, "LOGIN", {"username": user.username}, user_id=user.id,
               ip_address=request.client.host if request.client else None)
    return {"access_token": token, "token_type": "bearer", "role": user.role}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


_RESET_TOKEN_TTL = timedelta(minutes=30)


def _pwh_fragment(hashed_password: str) -> str:
    """Short fingerprint of the current password hash, embedded in reset
    tokens: once the password changes the fingerprint no longer matches, so
    every previously issued token dies — single-use without a token table."""
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send a password-reset link. Always answers the same way, so the
    endpoint can't be used to probe which emails have accounts."""
    generic = {"message": "If an account with that email exists, a reset link has been sent."}
    try:
        user = db.query(User).filter(User.email == req.email).first()
        if user is None:
            return generic
        token = create_access_token(
            {"sub": user.username, "purpose": "pwd_reset",
             "pwh": _pwh_fragment(user.hashed_password)},
            expires_delta=_RESET_TOKEN_TTL,
        )
        reset_link = f"{settings.frontend_url}/auth.html?reset_token={token}"
        sent = send_email(
            user.email,
            "Reset your Lexara password",
            f"Hi {user.username},\n\n"
            f"Someone requested a password reset for your Lexara account. "
            f"If this was you, open the link below within 30 minutes:\n\n"
            f"{reset_link}\n\n"
            f"If you didn't request this, you can safely ignore this email.\n",
        )
        if not sent:
            # SMTP not configured on this deployment: the link is written to
            # server logs only, so the operator can deliver it manually.
            logger.warning("password reset requested for %s but SMTP is not "
                           "configured — reset link: %s", user.email, reset_link)
        log_action(db, "PASSWORD_RESET_REQUESTED", {"username": user.username},
                   user_id=user.id)
    except Exception:
        logger.exception("forgot-password failed")
    return generic


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Set a new password using a reset token from the emailed link."""
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    invalid = HTTPException(status_code=400,
                            detail="This reset link is invalid or has expired. "
                                   "Please request a new one.")
    try:
        claims = decode_token(req.token)
    except (HTTPException, JWTError):
        # decode_token raises HTTPException(401) on bad/expired tokens;
        # for a reset link that is a 400 with a friendlier message.
        raise invalid
    if claims.get("purpose") != "pwd_reset":
        raise invalid
    user = db.query(User).filter(User.username == claims.get("sub")).first()
    if user is None or claims.get("pwh") != _pwh_fragment(user.hashed_password):
        raise invalid  # unknown user, or token already spent / password since changed
    try:
        user.hashed_password = hash_password(req.new_password)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _auth_500(e)
    log_action(db, "PASSWORD_RESET", {"username": user.username}, user_id=user.id)
    return {"message": "Password updated. You can now sign in."}
