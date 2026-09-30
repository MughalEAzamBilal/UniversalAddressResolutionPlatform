from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.address import Address, AddressType, LocationScope, AddressVisibility
from app.models.address_version import AddressVersion


class AddressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, address_id: int) -> Optional[Address]:
        return self.db.query(Address).filter(Address.id == address_id).first()

    def get_by_public_id(self, public_id: str) -> Optional[Address]:
        """Lookup by lowercase normalized public ID."""
        clean = public_id.strip().lower()
        return self.db.query(Address).filter(Address.public_id == clean).first()

    def list_by_user(
        self,
        user_id: int,
        search: Optional[str] = None,
        address_type: Optional[str] = None,
        location_scope: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Address]:
        query = self.db.query(Address).filter(Address.user_id == user_id)

        if is_active is not None:
            query = query.filter(Address.is_active == is_active)
        if address_type:
            query = query.filter(Address.address_type == address_type.upper())
        if location_scope:
            query = query.filter(Address.location_scope == location_scope.upper())
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Address.public_id.ilike(s),
                    Address.city.ilike(s),
                    Address.country.ilike(s),
                    Address.address_text.ilike(s),
                    Address.recipient_name.ilike(s),
                    Address.landmark.ilike(s)
                )
            )
        return query.order_by(Address.created_at.desc()).offset(skip).limit(limit).all()

    def count_by_user(self, user_id: int) -> int:
        return self.db.query(Address).filter(Address.user_id == user_id).count()

    def list_all(
        self,
        search: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        address_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Address]:
        query = self.db.query(Address)

        if is_active is not None:
            query = query.filter(Address.is_active == is_active)
        if city:
            query = query.filter(Address.city.ilike(f"%{city.strip()}%"))
        if country:
            query = query.filter(Address.country.ilike(f"%{country.strip()}%"))
        if address_type:
            query = query.filter(Address.address_type == address_type.upper())
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Address.public_id.ilike(s),
                    Address.city.ilike(s),
                    Address.country.ilike(s),
                    Address.address_text.ilike(s),
                    Address.recipient_name.ilike(s)
                )
            )
        return query.order_by(Address.created_at.desc()).offset(skip).limit(limit).all()

    def get_stats(self) -> dict:
        total = self.db.query(Address).count()
        active = self.db.query(Address).filter(Address.is_active == True).count()
        inactive = total - active
        local = self.db.query(Address).filter(Address.location_scope == LocationScope.LOCAL).count()
        intl = self.db.query(Address).filter(Address.location_scope == LocationScope.INTERNATIONAL).count()
        return {
            "total_addresses": total,
            "active_addresses": active,
            "inactive_addresses": inactive,
            "local_addresses": local,
            "international_addresses": intl,
        }

    def create(self, address: Address) -> Address:
        self.db.add(address)
        self.db.commit()
        self.db.refresh(address)
        return address

    def update(self, address: Address) -> Address:
        self.db.commit()
        self.db.refresh(address)
        return address

    def delete(self, address: Address) -> None:
        self.db.delete(address)
        self.db.commit()

    def create_version(self, version: AddressVersion) -> AddressVersion:
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_versions(self, address_id: int) -> List[AddressVersion]:
        return self.db.query(AddressVersion).filter(
            AddressVersion.address_id == address_id
        ).order_by(AddressVersion.version_number.desc()).all()
