from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address_id = Column(Integer, ForeignKey("addresses.id", ondelete="CASCADE"), nullable=True, index=True)
    public_id = Column(String(6), index=True, nullable=False)
    accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    referrer = Column(String(512), nullable=True)
    success = Column(Boolean, default=True, nullable=False)

    address = relationship("Address", back_populates="access_logs")


Index("ix_access_logs_time_success", AccessLog.accessed_at, AccessLog.success)
