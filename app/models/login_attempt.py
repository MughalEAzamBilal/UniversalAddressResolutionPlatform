from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database.base import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    identifier = Column(String(128), index=True, nullable=False)
    attempt_type = Column(String(32), default="PASSWORD", nullable=False)  # PASSWORD or EDIT_ID
    ip_address = Column(String(64), nullable=True)
    success = Column(Boolean, default=False, nullable=False)
    attempted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
