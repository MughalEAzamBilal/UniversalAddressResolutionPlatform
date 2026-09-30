from typing import Optional
from flask import request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole, AccountStatus
from app.repositories.user_repository import UserRepository
from app.core.exceptions import AppError


def get_client_ip(req=None) -> str:
    """Extract client IP handling proxies."""
    if req is None:
        req = request
    x_forwarded = req.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return req.remote_addr or "127.0.0.1"


def get_api_current_user() -> User:
    """Extract and validate authenticated user from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
    elif request.cookies.get("session_token"):
        token = request.cookies.get("session_token")
    elif request.cookies.get("edit_session_token"):
        token = request.cookies.get("edit_session_token")

    if not token:
        raise AppError("Authentication required.", status_code=401)

    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise AppError("Invalid or expired token.", status_code=401)

    db: Session = get_db()
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(payload.get("sub")))
    if not user or user.account_status != AccountStatus.ACTIVE:
        raise AppError("User account is inactive or not found.", status_code=401)

    return user


def get_api_admin() -> User:
    user = get_api_current_user()
    if user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        raise AppError("Administrator privileges required.", status_code=403)
    return user
