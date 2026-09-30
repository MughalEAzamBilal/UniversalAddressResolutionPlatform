import secrets
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.user import User, UserRole, AccountStatus
from app.models.login_attempt import LoginAttempt
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegisterRequest
from app.core.security import (
    hash_password,
    verify_password,
    hash_edit_id,
    normalize_edit_id,
    verify_edit_id,
    create_access_token
)
from app.core.exceptions import InvalidCredentialsError, AccountLockedError, AppError
from app.core.config import get_settings
from app.core.logging import logger
from app.services.edit_id_service import EditIdService
from app.services.public_id_generator import public_id_generator


settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register(self, req: UserRegisterRequest, public_id: Optional[str] = None) -> Tuple[User, str]:
        """
        Register a new user.
        Generates Edit ID from public_id and personal fields, hashes it with Argon2,
        hashes password, and creates the user.
        Returns (user, raw_edit_id) so the user can be shown their Edit ID once.
        """
        # Check uniqueness
        if self.user_repo.get_by_username(req.username):
            raise AppError("Username is already taken.", status_code=409)
        if self.user_repo.get_by_email(req.email):
            raise AppError("Email is already registered.", status_code=409)

        pub_id = (public_id or public_id_generator.generate(self.db)).lower()

        # Generate unique Edit ID (cannot be identical or same)
        raw_edit_id = EditIdService.generate_unique_edit_id(
            db=self.db,
            public_id=pub_id,
            father_name=req.father_name,
            mother_name=req.mother_name,
            cnic_or_id_card=req.cnic_or_id_card,
            date_of_birth=req.date_of_birth
        )
        hashed_edit_id = hash_edit_id(raw_edit_id)
        hashed_pw = hash_password(req.password)

        user = User(
            username=req.username.strip(),
            email=req.email.strip().lower(),
            phone=req.phone.strip() if req.phone else None,
            full_name=req.full_name.strip(),
            father_name=req.father_name.strip(),
            mother_name=req.mother_name.strip(),
            cnic_or_id_card=req.cnic_or_id_card.strip(),
            date_of_birth=req.date_of_birth,
            password_hash=hashed_pw,
            edit_id_hash=hashed_edit_id,
            public_id=pub_id,
            role=UserRole.USER,
            account_status=AccountStatus.ACTIVE
        )
        created_user = self.user_repo.create(user)
        logger.info(f"User registered successfully: {created_user.username} (Edit ID: {raw_edit_id})")
        return created_user, raw_edit_id

    def register_or_get_by_edit_id(
        self,
        full_name: str,
        father_name: str,
        mother_name: str,
        cnic_or_id_card: str,
        date_of_birth: date,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        public_id: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Create a new user with a guaranteed unique Edit ID without requiring a password.
        Edit IDs cannot be identical or same; format is [PublicID][FatherInitial][MotherInitial][CNICLast3][DOBYY].
        Returns (user, raw_edit_id).
        """
        pub_id = (public_id or public_id_generator.generate(self.db)).lower()
        raw_edit_id = EditIdService.generate_unique_edit_id(
            db=self.db,
            public_id=pub_id,
            father_name=father_name,
            mother_name=mother_name,
            cnic_or_id_card=cnic_or_id_card,
            date_of_birth=date_of_birth
        )
        normalized_edit_id = normalize_edit_id(raw_edit_id)

        # Generate a unique username & email if not provided
        sanitized_suffix = normalized_edit_id.lower().replace("-", "_")
        base_username = f"user_{sanitized_suffix}"
        candidate_username = base_username
        suffix = 1
        while self.user_repo.get_by_username(candidate_username):
            candidate_username = f"{base_username}_{suffix}"
            suffix += 1

        user_email = email.strip().lower() if email and email.strip() else f"{candidate_username}@universaladdress.local"
        if self.user_repo.get_by_email(user_email):
            user_email = f"{candidate_username}_{int(datetime.now().timestamp())}@universaladdress.local"

        hashed_edit_id = hash_edit_id(raw_edit_id)
        # Random secure unusable password hash
        random_secret = secrets.token_urlsafe(32)
        hashed_pw = hash_password(random_secret)

        user = User(
            username=candidate_username,
            email=user_email,
            phone=phone.strip() if phone else None,
            full_name=full_name.strip(),
            father_name=father_name.strip(),
            mother_name=mother_name.strip(),
            cnic_or_id_card=cnic_or_id_card.strip(),
            date_of_birth=date_of_birth,
            password_hash=hashed_pw,
            edit_id_hash=hashed_edit_id,
            public_id=pub_id,
            role=UserRole.USER,
            account_status=AccountStatus.ACTIVE
        )
        created_user = self.user_repo.create(user)
        logger.info(f"User created via Edit ID workflow with unique Edit ID: {created_user.username} (Edit ID: {raw_edit_id})")
        return created_user, raw_edit_id

    def authenticate_password(self, identifier: str, password: str, ip_address: Optional[str] = None) -> User:

        """Authenticate user with username/email and password."""
        user = self.user_repo.get_by_username_or_email(identifier)
        now = datetime.now(timezone.utc)

        if not user:
            # Fake hash check to mitigate timing attacks
            hash_password("dummy-password-check")
            self._log_attempt(identifier, "PASSWORD", ip_address, False)
            raise InvalidCredentialsError("Invalid username/email or password.")

        if user.account_status != AccountStatus.ACTIVE:
            raise AppError("Account is suspended or inactive.", status_code=403)

        if user.is_locked():
            raise AccountLockedError(f"Account locked until {user.locked_until.strftime('%H:%M:%S UTC')}.")

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
                logger.warning(f"User {user.username} locked out due to failed password attempts.")
            self.db.commit()
            self._log_attempt(user.username, "PASSWORD", ip_address, False)
            raise InvalidCredentialsError("Invalid username/email or password.")

        # Success!
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        self.db.commit()
        self._log_attempt(user.username, "PASSWORD", ip_address, True)
        return user

    def create_user_tokens(self, user: User) -> dict:
        """Create standard access token for user."""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "type": "access"
        }
        token = create_access_token(token_data)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        }

    def create_edit_session_token(self, user: User) -> dict:
        """Create specialized short-lived token for Edit ID session."""
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "type": "edit_session"
        }
        token = create_access_token(token_data, expires_delta=timedelta(minutes=settings.EDIT_SESSION_EXPIRE_MINUTES))
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "username": user.username
        }

    def _log_attempt(self, identifier: str, attempt_type: str, ip: Optional[str], success: bool):
        attempt = LoginAttempt(
            identifier=identifier[:100],
            attempt_type=attempt_type,
            ip_address=ip,
            success=success,
            attempted_at=datetime.now(timezone.utc)
        )
        self.db.add(attempt)
        self.db.commit()
