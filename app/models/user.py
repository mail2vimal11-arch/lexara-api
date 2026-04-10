"""User model with role-based access."""

import uuid
from sqlalchemy import Column, String, DateTime, func
from app.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="procurement")  # admin | procurement | legal
    created_at = Column(DateTime, server_default=func.now())
