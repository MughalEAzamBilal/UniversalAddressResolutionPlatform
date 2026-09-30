import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db, settings
from app.web.deps import require_web_admin
from app.repositories.user_repository import UserRepository
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.services.public_id_generator import public_id_generator
from app.services.address_service import AddressService
from app.services.audit_service import AuditService
from app.services.ad_service import AdService
from app.models.advertisement import AdPlacement, AdType
from app.models.user import AccountStatus
from starlette.templating import Jinja2Templates

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    addr_repo = AddressRepository(db)
    log_repo = LogRepository(db)

    addr_stats = addr_repo.get_stats()
    res_stats = log_repo.get_resolution_stats()

    stats = {
        "total_users": user_repo.count_users(),
        "total_addresses": addr_stats["total_addresses"],
        "active_addresses": addr_stats["active_addresses"],
        "inactive_addresses": addr_stats["inactive_addresses"],
        "local_addresses": addr_stats["local_addresses"],
        "international_addresses": addr_stats["international_addresses"],
        "today_resolutions": res_stats["today_resolutions"],
        "failed_resolutions": res_stats["failed_resolutions"],
    }

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "active_nav": "admin_dashboard"
        }
    )


@router.get("/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    search: Optional[str] = None,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    users = user_repo.list_users(search=search, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "request": request,
            "current_user": current_user,
            "users": users,
            "search": search,
            "active_nav": "admin_users"
        }
    )


@router.post("/users/{user_id}/toggle-status")
def admin_toggle_user_status(
    user_id: int,
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if user:
        user.account_status = AccountStatus.INACTIVE if user.account_status == AccountStatus.ACTIVE else AccountStatus.ACTIVE
        user_repo.update(user)
        audit = AuditService(db)
        audit.log_action(current_user.id, "TOGGLE_USER_STATUS", "USER", str(user.id), f"Set to {user.account_status}")
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/addresses", response_class=HTMLResponse)
def admin_addresses_page(
    request: Request,
    search: Optional[str] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    addr_repo = AddressRepository(db)
    addresses = addr_repo.list_all(search=search, city=city, country=country, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="admin/addresses.html",
        context={
            "request": request,
            "current_user": current_user,
            "addresses": addresses,
            "search": search,
            "city": city,
            "country": country,
            "active_nav": "admin_addresses"
        }
    )


@router.post("/addresses/{public_id}/toggle-status")
def admin_toggle_address_status(
    public_id: str,
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    service = AddressService(db)
    addr = service.get_by_public_id(public_id)
    if addr:
        service.set_active_status(public_id, user_id=current_user.id, is_active=not addr.is_active, is_admin=True)
        audit = AuditService(db)
        audit.log_action(current_user.id, "TOGGLE_ADDRESS_STATUS", "ADDRESS", public_id, f"Set to {not addr.is_active}")
    
    referrer = request.headers.get("referer", "/admin/addresses")
    return RedirectResponse(url=referrer, status_code=303)


@router.get("/links", response_class=HTMLResponse)
def admin_links_page(
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    addr_repo = AddressRepository(db)
    addresses = addr_repo.list_all(limit=100)
    return templates.TemplateResponse(
        request=request,
        name="admin/links.html",
        context={
            "request": request,
            "current_user": current_user,
            "addresses": addresses,
            "base_url": settings.PUBLIC_BASE_URL,
            "active_nav": "admin_links"
        }
    )


@router.get("/generator", response_class=HTMLResponse)
def admin_generator_page(
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    year = datetime.now(timezone.utc).year
    stats = public_id_generator.get_pattern_statistics(db, year)
    return templates.TemplateResponse(
        request=request,
        name="admin/generator.html",
        context={
            "request": request,
            "current_user": current_user,
            "year": year,
            "patterns": stats,
            "active_nav": "admin_generator"
        }
    )


@router.get("/logs", response_class=HTMLResponse)
def admin_logs_page(
    request: Request,
    search: Optional[str] = None,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    log_repo = LogRepository(db)
    logs = log_repo.list_access_logs(search=search, limit=100)
    return templates.TemplateResponse(
        request=request,
        name="admin/logs.html",
        context={
            "request": request,
            "current_user": current_user,
            "logs": logs,
            "search": search,
            "active_nav": "admin_logs"
        }
    )


@router.get("/system/backup")
def admin_backup_database(
    current_user=Depends(require_web_admin)
):
    db_url = settings.DATABASE_URL
    src_path = db_url.replace("sqlite:///", "")
    if os.path.exists(src_path):
        backups_dir = os.path.join(os.path.dirname(src_path), "backups")
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(backups_dir, f"backup_{timestamp}.db")
        
        src_conn = sqlite3.connect(src_path)
        dest_conn = sqlite3.connect(dest_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()

    return RedirectResponse(url="/admin?backup=success", status_code=303)


@router.get("/ads", response_class=HTMLResponse)
def admin_ads_page(
    request: Request,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    ad_service = AdService(db)
    ads = ad_service.get_all_ads()
    stats = ad_service.get_stats()
    return templates.TemplateResponse(
        request=request,
        name="admin/ads.html",
        context={
            "request": request,
            "current_user": current_user,
            "ads": ads,
            "stats": stats,
            "placements": AdPlacement.ALL,
            "types": AdType.ALL,
            "active_nav": "admin_ads"
        }
    )


@router.post("/ads/create")
def admin_create_ad(
    title: str = Form(...),
    placement: str = Form(...),
    ad_type: str = Form(AdType.GOOGLE_ADSENSE),
    code_snippet: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    target_url: Optional[str] = Form(None),
    display_order: int = Form(0),
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    ad_service = AdService(db)
    ad_service.create_ad(
        title=title,
        placement=placement,
        ad_type=ad_type,
        code_snippet=code_snippet,
        image_url=image_url,
        target_url=target_url,
        display_order=display_order
    )
    return RedirectResponse(url="/admin/ads?success=created", status_code=303)


@router.post("/ads/{ad_id}/toggle")
def admin_toggle_ad(
    ad_id: int,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    ad_service = AdService(db)
    ad_service.toggle_active(ad_id)
    return RedirectResponse(url="/admin/ads?success=toggled", status_code=303)


@router.post("/ads/{ad_id}/delete")
def admin_delete_ad(
    ad_id: int,
    current_user=Depends(require_web_admin),
    db: Session = Depends(get_db)
):
    ad_service = AdService(db)
    ad_service.delete_ad(ad_id)
    return RedirectResponse(url="/admin/ads?success=deleted", status_code=303)

