import re
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.services.address_formatter import AddressFormatter
from app.schemas.resolver import ResolutionResponse
from app.core.exceptions import AddressNotFoundError, AddressDeactivatedError, AddressPrivateError
from app.models.address import AddressVisibility
from app.core.logging import logger


class ResolverService:
    def __init__(self, db: Session):
        self.db = db
        self.addr_repo = AddressRepository(db)
        self.log_repo = LogRepository(db)

    def resolve(
        self,
        public_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> ResolutionResponse:
        """
        Public resolver business logic:
        1. Normalizes public ID to lowercase.
        2. Validates format (6 alphanumeric characters).
        3. Queries address by canonical lowercase public_id.
        4. Validates active status and public visibility.
        5. Logs access attempt into access_logs.
        6. Formats clean presentation without exposing sensitive fields.
        """
        normalized_id = public_id.strip().lower()

        # Validate 6-character format
        if not re.match(r"^[a-z0-9]{6}$", normalized_id):
            self.log_repo.log_access(
                public_id=normalized_id[:6],
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                success=False
            )
            raise AddressNotFoundError("Invalid Public Address ID format.")

        addr = self.addr_repo.get_by_public_id(normalized_id)

        if not addr:
            self.log_repo.log_access(
                public_id=normalized_id,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                success=False
            )
            logger.info(f"Resolution failed: Address not found for ID '{normalized_id}'")
            raise AddressNotFoundError("Address not found.")

        if not addr.is_active:
            self.log_repo.log_access(
                public_id=normalized_id,
                address_id=addr.id,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                success=False
            )
            logger.info(f"Resolution blocked: Address '{normalized_id}' is deactivated.")
            raise AddressDeactivatedError("This address is currently unavailable.")

        if addr.visibility == AddressVisibility.PRIVATE:
            self.log_repo.log_access(
                public_id=normalized_id,
                address_id=addr.id,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                success=False
            )
            logger.info(f"Resolution blocked: Address '{normalized_id}' is marked private.")
            raise AddressPrivateError("This address is private.")

        # Access success!
        self.log_repo.log_access(
            public_id=normalized_id,
            address_id=addr.id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            success=True
        )

        all_formats = AddressFormatter.format_all_views(addr)
        display_text = addr.address_text or all_formats["FULL"]

        # Generate Google Maps driving directions link
        import urllib.parse
        if addr.latitude is not None and addr.longitude is not None:
            driving_directions_url = f"https://www.google.com/maps/dir/?api=1&destination={addr.latitude},{addr.longitude}&travelmode=driving"
        else:
            query = display_text if display_text else f"{addr.city}, {addr.country}"
            encoded = urllib.parse.quote_plus(query)
            driving_directions_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded}&travelmode=driving"

        effective_destination = addr.destination_url or driving_directions_url

        logger.info(f"Resolved address '{normalized_id}' successfully.")
        return ResolutionResponse(
            public_id=addr.public_id,
            address_type=addr.address_type,
            location_scope=addr.location_scope,
            display_text=display_text,
            city=addr.city,
            country=addr.country,
            postal_code=addr.postal_code,
            destination_url=effective_destination,
            driving_directions_url=driving_directions_url,
            redirect_seconds=addr.redirect_seconds,
            latitude=addr.latitude,
            longitude=addr.longitude,
            all_formats=all_formats
        )
