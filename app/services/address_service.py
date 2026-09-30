import json
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.address import Address, AddressType, LocationScope, AddressVisibility
from app.models.address_version import AddressVersion
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate
from app.services.public_id_generator import public_id_generator
from app.services.address_formatter import AddressFormatter
from app.core.security import validate_destination_url
from app.core.exceptions import AddressNotFoundError, AppError
from app.core.logging import logger


class AddressService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AddressRepository(db)

    def _serialize_address_snapshot(self, addr: Address) -> str:
        """Create JSON snapshot of all fields for version history."""
        return json.dumps({
            "public_id": addr.public_id,
            "address_type": addr.address_type,
            "location_scope": addr.location_scope,
            "visibility": addr.visibility,
            "recipient_name": addr.recipient_name,
            "business_name": addr.business_name,
            "country": addr.country,
            "country_code": addr.country_code,
            "province_state": addr.province_state,
            "region_division": addr.region_division,
            "district": addr.district,
            "tehsil": addr.tehsil,
            "city": addr.city,
            "town": addr.town,
            "area": addr.area,
            "locality": addr.locality,
            "street": addr.street,
            "road": addr.road,
            "house_number": addr.house_number,
            "building": addr.building,
            "floor": addr.floor,
            "flat": addr.flat,
            "landmark": addr.landmark,
            "postal_code": addr.postal_code,
            "latitude": addr.latitude,
            "longitude": addr.longitude,
            "address_text": addr.address_text,
            "destination_url": addr.destination_url,
            "redirect_seconds": addr.redirect_seconds,
            "is_active": addr.is_active,
            "snapshot_at": datetime.now(timezone.utc).isoformat()
        }, indent=2)

    def create_address(self, user_id: int, data: AddressCreate, year: Optional[int] = None, public_id: Optional[str] = None) -> Address:
        """
        Create a new address.
        Uses allocated or provided Public Address ID (e.g. ab1226) or generates one.
        Calculates address text.
        Stores initial version snapshot (version 1).
        """
        clean_destination = validate_destination_url(data.destination_url)
        assigned_pub_id = None
        if public_id:
            assigned_pub_id = public_id.strip()[:6].lower()
        else:
            # Check if user has an assigned public_id that is not yet used in addresses
            from app.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.public_id:
                existing = self.db.query(Address).filter(Address.public_id == user.public_id.lower()).first()
                if not existing:
                    assigned_pub_id = user.public_id.lower()

        if not assigned_pub_id:
            assigned_pub_id = public_id_generator.generate(self.db, year=year)

        clean_recipient = data.recipient_name
        if not clean_recipient or not str(clean_recipient).strip():
            from app.models.user import User
            user_obj = self.db.query(User).filter(User.id == user_id).first()
            clean_recipient = user_obj.full_name if user_obj and user_obj.full_name else "Resident"

        address = Address(
            public_id=assigned_pub_id,
            user_id=user_id,
            address_type=data.address_type,
            location_scope=data.location_scope,
            visibility=data.visibility,
            recipient_name=clean_recipient.strip(),
            business_name=data.business_name,
            country=data.country,
            country_code=data.country_code,
            province_state=data.province_state,
            region_division=data.region_division,
            district=data.district,
            tehsil=data.tehsil,
            city=data.city,
            town=data.town,
            area=data.area,
            locality=data.locality,
            street=data.street,
            road=data.road,
            house_number=data.house_number,
            building=data.building,
            floor=data.floor,
            flat=data.flat,
            landmark=data.landmark,
            postal_code=data.postal_code,
            latitude=data.latitude,
            longitude=data.longitude,
            destination_url=clean_destination,
            redirect_seconds=data.redirect_seconds,
            is_active=True,
            address_text=""  # temporarily empty to compute below
        )
        address.address_text = AddressFormatter.format_full(address)
        created = self.repo.create(address)

        # Create Version 1 snapshot
        snapshot_json = self._serialize_address_snapshot(created)
        version = AddressVersion(
            address_id=created.id,
            version_number=1,
            address_snapshot=snapshot_json,
            changed_by=user_id
        )
        self.repo.create_version(version)
        logger.info(f"Address created successfully. Public ID: {created.public_id} for user {user_id}")
        return created

    def update_address(
        self,
        public_id: str,
        user_id: int,
        data: AddressUpdate,
        is_admin: bool = False
    ) -> Address:
        """
        Update address content.
        CRITICAL: Public Address ID remains UNCHANGED!
        Saves a new snapshot into address_versions.
        """
        address = self.repo.get_by_public_id(public_id)
        if not address:
            raise AddressNotFoundError("Address not found.")

        if not is_admin and address.user_id != user_id:
            raise AppError("Permission denied: You do not own this address.", status_code=403)

        # Update provided fields
        update_data = data.model_dump(exclude_unset=True)
        if "destination_url" in update_data:
            update_data["destination_url"] = validate_destination_url(update_data["destination_url"])
        if "recipient_name" in update_data and (update_data["recipient_name"] is None or not str(update_data["recipient_name"]).strip()):
            del update_data["recipient_name"]

        for field, value in update_data.items():
            if hasattr(address, field) and field not in ("id", "public_id", "user_id", "created_at"):
                setattr(address, field, value)

        # Re-compute formatted text
        address.address_text = AddressFormatter.format_full(address)
        address.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(address)

        # Determine next version number
        existing_versions = self.repo.get_versions(address.id)
        next_version_num = (existing_versions[0].version_number + 1) if existing_versions else 1

        # Create Version snapshot
        snapshot_json = self._serialize_address_snapshot(updated)
        new_version = AddressVersion(
            address_id=updated.id,
            version_number=next_version_num,
            address_snapshot=snapshot_json,
            changed_by=user_id
        )
        self.repo.create_version(new_version)
        logger.info(f"Address {address.public_id} updated to version {next_version_num}")
        return updated

    def get_by_public_id(self, public_id: str) -> Address:
        addr = self.repo.get_by_public_id(public_id)
        if not addr:
            raise AddressNotFoundError("Address not found.")
        return addr

    def set_active_status(self, public_id: str, user_id: int, is_active: bool, is_admin: bool = False) -> Address:
        addr = self.get_by_public_id(public_id)
        if not is_admin and addr.user_id != user_id:
            raise AppError("Permission denied.", status_code=403)
        addr.is_active = is_active
        addr.updated_at = datetime.now(timezone.utc)
        return self.repo.update(addr)

    def delete_address(self, public_id: str, user_id: int, is_admin: bool = False) -> None:
        addr = self.get_by_public_id(public_id)
        if not is_admin and addr.user_id != user_id:
            raise AppError("Permission denied.", status_code=403)
        self.repo.delete(addr)
        logger.info(f"Address {public_id} deleted by user {user_id}")

    def list_user_addresses(self, user_id: int, **kwargs) -> List[Address]:
        return self.repo.list_by_user(user_id, **kwargs)

    def get_versions(self, public_id: str, user_id: int, is_admin: bool = False) -> List[AddressVersion]:
        addr = self.get_by_public_id(public_id)
        if not is_admin and addr.user_id != user_id:
            raise AppError("Permission denied.", status_code=403)
        return self.repo.get_versions(addr.id)
