from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base


class AddressType:
    PERSONAL = "PERSONAL"
    RESIDENTIAL = "RESIDENTIAL"
    DELIVERY = "DELIVERY"
    BUSINESS = "BUSINESS"
    POSTAL = "POSTAL"
    LANDMARK = "LANDMARK"
    TEMPORARY = "TEMPORARY"
    OTHER = "OTHER"

    ALL = [PERSONAL, RESIDENTIAL, DELIVERY, BUSINESS, POSTAL, LANDMARK, TEMPORARY, OTHER]


class LocationScope:
    LOCAL = "LOCAL"
    INTERNATIONAL = "INTERNATIONAL"

    ALL = [LOCAL, INTERNATIONAL]


class AddressVisibility:
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    UNLISTED = "UNLISTED"

    ALL = [PUBLIC, PRIVATE, UNLISTED]


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # The canonical 6-character public ID, always stored lowercase
    public_id = Column(String(6), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    address_type = Column(String(32), default=AddressType.PERSONAL, index=True, nullable=False)
    location_scope = Column(String(32), default=LocationScope.LOCAL, index=True, nullable=False)
    visibility = Column(String(32), default=AddressVisibility.PUBLIC, index=True, nullable=False)

    recipient_name = Column(String(128), default="Resident", nullable=False)  # Compulsory for both personal and business
    business_name = Column(String(128), nullable=True)   # Company / Store name for business address

    # Location fields
    country = Column(String(128), default="Pakistan", index=True, nullable=False)
    country_code = Column(String(8), default="PK", nullable=False)
    province_state = Column(String(128), nullable=True)
    region_division = Column(String(128), nullable=True)
    district = Column(String(128), nullable=True)
    tehsil = Column(String(128), nullable=True)
    city = Column(String(128), index=True, nullable=False)
    town = Column(String(128), nullable=True)
    area = Column(String(128), nullable=True)
    locality = Column(String(128), nullable=True)

    # Street fields
    street = Column(String(128), nullable=True)
    road = Column(String(128), nullable=True)
    house_number = Column(String(64), nullable=True)
    building = Column(String(128), nullable=True)
    floor = Column(String(32), nullable=True)
    flat = Column(String(32), nullable=True)
    landmark = Column(String(255), nullable=True)
    postal_code = Column(String(32), nullable=True)

    # Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Cached formatted text representation
    address_text = Column(Text, nullable=False)

    # Redirection
    destination_url = Column(String(1024), nullable=True)
    redirect_seconds = Column(Integer, default=3, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="addresses")
    versions = relationship("AddressVersion", back_populates="address", cascade="all, delete-orphan", order_by="desc(AddressVersion.version_number)")
    access_logs = relationship("AccessLog", back_populates="address", cascade="all, delete-orphan")


# Index composite queries
Index("ix_addresses_country_city", Address.country, Address.city)
Index("ix_addresses_type_scope", Address.address_type, Address.location_scope)
