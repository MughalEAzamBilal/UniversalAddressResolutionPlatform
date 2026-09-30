from functools import wraps
from typing import Optional
from flask import request, session, redirect, g
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole, AccountStatus
from app.repositories.user_repository import UserRepository


def get_client_ip() -> str:
    """Extract client IP handling proxies / X-Forwarded-For."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def get_current_web_user() -> Optional[User]:
    """Retrieve user from Flask session or session cookies. Returns None if not logged in."""
    if hasattr(g, "current_user") and g.current_user is not None:
        return g.current_user

    user_id = session.get("user_id")
    db: Session = get_db()
    user_repo = UserRepository(db)

    if user_id:
        user = user_repo.get_by_id(int(user_id))
        if user and user.account_status == AccountStatus.ACTIVE:
            g.current_user = user
            return user

    # Fallback to session tokens in cookies if present
    token = request.cookies.get("session_token") or request.cookies.get("edit_session_token")
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            user = user_repo.get_by_id(int(payload.get("sub")))
            if user and user.account_status == AccountStatus.ACTIVE:
                session["user_id"] = user.id
                g.current_user = user
                return user

    g.current_user = None
    return None


def require_web_user(f):
    """Decorator requiring an authenticated user; otherwise redirects to /edit."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_web_user()
        if not user:
            return redirect(f"/edit?next={request.path}", code=303)
        return f(*args, **kwargs)
    return decorated_function


def require_web_admin(f):
    """Decorator requiring admin role; otherwise redirects to /dashboard."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_web_user()
        if not user:
            return redirect(f"/3210325048745?next={request.path}", code=303)
        if user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MODERATOR):
            return redirect("/dashboard", code=303)
        return f(*args, **kwargs)
    return decorated_function
