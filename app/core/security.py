import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from urllib.parse import urlparse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from app.core.config import get_settings
from app.core.exceptions import UnsafeDestinationError

ph = PasswordHasher()
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def normalize_edit_id(edit_id: str) -> str:
    """Normalize Edit ID: uppercase and stripped of all whitespace."""
    return "".join(edit_id.upper().split())


def hash_edit_id(edit_id: str) -> str:
    """
    Hash Edit ID using Argon2id.
    Normalizes Edit ID first so verification is case-insensitive.
    """
    normalized = normalize_edit_id(edit_id)
    return ph.hash(normalized)


def verify_edit_id(plain_edit_id: str, hashed_edit_id: str) -> bool:
    """Verify raw Edit ID against stored hash (case-insensitive)."""
    normalized = normalize_edit_id(plain_edit_id)
    try:
        return ph.verify(hashed_edit_id, normalized)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create secure signed access token."""
    s = URLSafeTimedSerializer(settings.SECRET_KEY, salt="access-token")
    return s.dumps(data)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate access token."""
    s = URLSafeTimedSerializer(settings.SECRET_KEY, salt="access-token")
    try:
        max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return s.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired, Exception):
        return None


def validate_destination_url(url: Optional[str]) -> Optional[str]:
    """
    Validate that destination URL uses only http or https scheme.
    Prevents open redirect vulnerabilities (e.g. javascript:, data:, file:).
    Returns normalized clean URL string.
    """
    if not url:
        return None
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise UnsafeDestinationError()
    if not parsed.netloc:
        raise UnsafeDestinationError("Destination URL must include a valid host.")
    return url


class InMemoryRateLimiter:
    """
    Lightweight sliding-window rate limiter for brute-force protection.
    Tracks requests per key (e.g. IP or username or public_id).
    """
    def __init__(self):
        self.requests: Dict[str, list[float]] = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        
        # Clean older entries
        if key in self.requests:
            self.requests[key] = [t for t in self.requests[key] if t > window_start]
        else:
            self.requests[key] = []

        if len(self.requests[key]) >= max_requests:
            return False

        self.requests[key].append(now)
        return True


rate_limiter = InMemoryRateLimiter()
