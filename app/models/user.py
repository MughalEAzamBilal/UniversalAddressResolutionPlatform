from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.orm import relationship
from app.database.base import Base


class UserRole:
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"
    USER = "USER"


class AccountStatus:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(32), nullable=True)
    full_name = Column(String(128), nullable=False)
    father_name = Column(String(128), nullable=False)
    mother_name = Column(String(128), nullable=False)
    cnic_or_id_card = Column(String(64), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    password_hash = Column(String(255), nullable=False)
    edit_id_hash = Column(String(255), nullable=False, index=True)
    public_id = Column(String(6), nullable=True, index=True)
    role = Column(String(32), default=UserRole.USER, nullable=False)
    account_status = Column(String(32), default=AccountStatus.ACTIVE, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    addresses = relationship("Address", back_populates="user", cascade="all, delete-orphan")

    def is_locked(self) -> bool:
        if not self.locked_until:
            return False
        dt = self.locked_until
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > datetime.now(timezone.utc)
