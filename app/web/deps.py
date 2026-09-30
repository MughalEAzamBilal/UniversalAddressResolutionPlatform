from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole, AccountStatus
from app.repositories.user_repository import UserRepository


def get_current_web_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieve user from session cookie for HTML web pages. Returns None if not logged in."""
    token = request.cookies.get("session_token")
    if not token:
        # Check edit session cookie as fallback
        token = request.cookies.get("edit_session_token")

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    if not user or user.account_status != AccountStatus.ACTIVE:
        return None

    return user


def require_web_user(
    request: Request,
    current_user: Optional[User] = Depends(get_current_web_user)
) -> User:
    """Dependency that requires an authenticated user; otherwise redirects to /edit to enter Edit ID."""
    if not current_user:
        # In web routes, Edit ID is the way to access editing
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/edit?next={request.url.path}"}
        )
    return current_user


def require_web_admin(
    request: Request,
    current_user: User = Depends(require_web_user)
) -> User:
    """Dependency that requires admin role; otherwise redirects to /dashboard."""
    if current_user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MODERATOR):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/dashboard"}
        )
    return current_user
