from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import normalize_edit_id, hash_edit_id, verify_edit_id
from app.core.exceptions import InvalidEditIdError, AccountLockedError
from app.core.config import get_settings
from app.models.user import User, AccountStatus
from app.models.address import Address
from app.models.login_attempt import LoginAttempt
from app.core.logging import logger

settings = get_settings()


class EditIdService:
    @staticmethod
    def generate_edit_id(
        public_id: str,
        father_name: str,
        mother_name: str,
        cnic_or_id_card: str,
        date_of_birth: date
    ) -> str:
        """
        Generate Edit ID:
        Format: [PublicID][FatherInitial][MotherInitial][CNICLast3][DOBYY]
        Example: ab1226 + M + A + 123 + 91 -> ab1226MA12391 (13 characters)
        """
        clean_pub_id = public_id.strip()[:6].lower() if public_id else "aaaa00"
        f_initial = father_name.strip()[0].upper() if father_name and father_name.strip() else "X"
        m_initial = mother_name.strip()[0].upper() if mother_name and mother_name.strip() else "X"

        clean_cnic = "".join(filter(str.isalnum, cnic_or_id_card))
        cnic_suffix = clean_cnic[-3:] if len(clean_cnic) >= 3 else clean_cnic.zfill(3)

        dob_yy = date_of_birth.strftime("%y")
        raw_id = f"{clean_pub_id}{f_initial}{m_initial}{cnic_suffix}{dob_yy}"
        return raw_id

    @classmethod
    def is_edit_id_taken(cls, db: Session, raw_edit_id: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Check if an Edit ID is already assigned to any active user.
        Case-insensitively checks against existing hashed Edit IDs.
        """
        normalized = normalize_edit_id(raw_edit_id)
        # Fast path: check address owner if public_id is present
        if len(normalized) >= 6:
            pub_id = normalized[:6].lower()
            addr = db.query(Address).filter(Address.public_id == pub_id).first()
            if addr and addr.user and addr.user.account_status == AccountStatus.ACTIVE:
                if (not exclude_user_id or addr.user.id != exclude_user_id) and verify_edit_id(normalized, addr.user.edit_id_hash):
                    return True

        query = db.query(User).filter(User.account_status == AccountStatus.ACTIVE)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        users = query.all()
        for user in users:
            if verify_edit_id(normalized, user.edit_id_hash):
                return True
        return False

    @classmethod
    def generate_unique_edit_id(
        cls,
        db: Session,
        public_id: str,
        father_name: str,
        mother_name: str,
        cnic_or_id_card: str,
        date_of_birth: date,
        exclude_user_id: Optional[int] = None
    ) -> str:
        """
        Generate an Edit ID that is guaranteed to be unique across all active users.
        Format: [PublicID][FatherInitial][MotherInitial][CNICLast3][DOBYY]
        If a collision occurs on the base formula, attaches an incremental suffix (-2, -3, etc.).
        """
        base_id = cls.generate_edit_id(public_id, father_name, mother_name, cnic_or_id_card, date_of_birth)
        if not cls.is_edit_id_taken(db, base_id, exclude_user_id=exclude_user_id):
            return base_id

        suffix = 2
        while True:
            candidate_id = f"{base_id}-{suffix}"
            if not cls.is_edit_id_taken(db, candidate_id, exclude_user_id=exclude_user_id):
                return candidate_id
            suffix += 1

    @classmethod
    def verify_and_authenticate(cls, db: Session, raw_edit_id: str, ip_address: Optional[str] = None) -> User:
        """
        Authenticate user using Edit ID.
        Checks for account lockouts, matches against users' edit_id_hash,
        updates login attempts, and logs the event.
        """
        normalized_input = normalize_edit_id(raw_edit_id)
        if len(normalized_input) < 8:
            raise InvalidEditIdError("Invalid Edit ID format.")

        now = datetime.now(timezone.utc)
        matched_user: Optional[User] = None

        # Fast lookup by Public ID prefix if 6+ chars
        if len(normalized_input) >= 6:
            pub_id = normalized_input[:6].lower()
            addr = db.query(Address).filter(Address.public_id == pub_id).first()
            if addr and addr.user and addr.user.account_status == AccountStatus.ACTIVE:
                if verify_edit_id(normalized_input, addr.user.edit_id_hash):
                    matched_user = addr.user

        # Fallback check across all active users
        if not matched_user:
            users = db.query(User).filter(User.account_status == AccountStatus.ACTIVE).all()
            for user in users:
                if verify_edit_id(normalized_input, user.edit_id_hash):
                    matched_user = user
                    break

        if not matched_user:
            # Record failed attempt
            attempt = LoginAttempt(
                identifier=normalized_input[:4] + "***",
                attempt_type="EDIT_ID",
                ip_address=ip_address,
                success=False,
                attempted_at=now
            )
            db.add(attempt)
            db.commit()
            logger.warning(f"Failed Edit ID attempt from IP: {ip_address}")
            raise InvalidEditIdError("Invalid Edit ID provided.")

        # Check if matched user is locked
        if matched_user.is_locked():
            logger.warning(f"Locked user {matched_user.username} tried Edit ID login.")
            raise AccountLockedError(f"Account locked until {matched_user.locked_until.strftime('%H:%M:%S UTC')}.")

        # Successful verification! Reset failed login attempts
        matched_user.failed_login_attempts = 0
        matched_user.locked_until = None
        matched_user.last_login_at = now

        attempt = LoginAttempt(
            identifier=matched_user.username,
            attempt_type="EDIT_ID",
            ip_address=ip_address,
            success=True,
            attempted_at=now
        )
        db.add(attempt)
        db.commit()
        db.refresh(matched_user)
        logger.info(f"User {matched_user.username} authenticated via Edit ID.")
        return matched_user

    @classmethod
    def record_failed_attempt(cls, db: Session, user: User):
        """Increment failed attempts and lock if threshold exceeded."""
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_MINUTES)
            logger.warning(f"User {user.username} locked out until {user.locked_until}")
        db.commit()
