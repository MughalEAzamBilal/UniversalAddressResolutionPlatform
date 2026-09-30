from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.schemas.auth import UserRegisterRequest
from app.web.deps import get_current_web_user
from app.api.deps import get_client_ip
from app.core.exceptions import AppError
from app.core.config import get_settings
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/3210325048745", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: str = "",
    current_user=Depends(get_current_web_user)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "request": request,
            "next_url": next,
            "current_user": None,
            "active_nav": "login"
        }
    )


@router.post("/3210325048745", response_class=HTMLResponse)
@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate_password(username, password, ip_address=ip)
        token_data = auth_service.create_user_tokens(user)
        redirect_url = next if next and next.startswith("/") else "/dashboard"
        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key="session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except AppError as e:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": e.message,
                "next_url": next,
                "current_user": None
            },
            status_code=e.status_code
        )


@router.get("/register")
def register_page():
    return RedirectResponse(url="/address/new", status_code=303)


@router.post("/register")
def register_submit():
    return RedirectResponse(url="/address/new", status_code=303)


@router.get("/edit", response_class=HTMLResponse)
def edit_id_portal_page(
    request: Request,
    next: str = "",
    current_user=Depends(get_current_web_user)
):
    return templates.TemplateResponse(
        request=request,
        name="auth/edit_id_portal.html",
        context={
            "request": request,
            "next_url": next,
            "current_user": current_user,
            "active_nav": "edit_id"
        }
    )


@router.post("/edit", response_class=HTMLResponse)
def edit_id_portal_submit(
    request: Request,
    edit_id: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    try:
        user = EditIdService.verify_and_authenticate(db, edit_id, ip_address=ip)
        auth_service = AuthService(db)
        token_data = auth_service.create_edit_session_token(user)

        redirect_url = next if (next and next.startswith("/")) else "/my-addresses"
        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key="edit_session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except AppError as e:
        return templates.TemplateResponse(
            request=request,
            name="auth/edit_id_portal.html",
            context={
                "request": request,
                "error": e.message,
                "next_url": next,
                "current_user": None,
                "active_nav": "edit_id"
            },
            status_code=e.status_code
        )


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_token")
    response.delete_cookie("edit_session_token")
    return response
