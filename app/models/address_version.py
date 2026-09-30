from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base


class AddressVersion(Base):
    __tablename__ = "address_versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address_id = Column(Integer, ForeignKey("addresses.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number = Column(Integer, nullable=False)
    address_snapshot = Column(Text, nullable=False)  # JSON representation of all fields
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    address = relationship("Address", back_populates="versions")
    author = relationship("User")
