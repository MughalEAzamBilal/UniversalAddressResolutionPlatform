from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    EditIdLoginRequest,
    TokenResponse,
    EditSessionTokenResponse
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.api.deps import get_client_ip, get_current_user
from app.models.user import User
from app.core.security import rate_limiter
from app.core.exceptions import RateLimitExceededError, AppError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Returns user details and the one-time generated Edit ID.
    """
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(f"register_{ip}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please wait.")

    auth_service = AuthService(db)
    try:
        user, edit_id = auth_service.register(req)
        return {
            "message": "User registered successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
            },
            "edit_id": edit_id,
            "notice": "Please save your Edit ID securely. It allows you to access and edit your addresses."
        }
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """Standard password login returning JWT access token."""
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(f"login_{ip}", max_requests=15, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please wait.")

    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate_password(req.username_or_email, req.password, ip_address=ip)
        return auth_service.create_user_tokens(user)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/edit-id-login", response_model=EditSessionTokenResponse)
def edit_id_login(req: EditIdLoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Edit ID verification endpoint.
    Case-insensitive verification generating a secure editing session token.
    """
    ip = get_client_ip(request)
    if not rate_limiter.is_allowed(f"editid_{ip}", max_requests=8, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many Edit ID verification attempts.")

    try:
        user = EditIdService.verify_and_authenticate(db, req.edit_id, ip_address=ip)
        auth_service = AuthService(db)
        return auth_service.create_edit_session_token(user)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve current authenticated user profile."""
    return current_user
