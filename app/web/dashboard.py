from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.web.deps import require_web_user
from app.services.address_service import AddressService
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.core.config import get_settings
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/dashboard", response_class=HTMLResponse)
def user_dashboard(
    request: Request,
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    addr_repo = AddressRepository(db)
    log_repo = LogRepository(db)

    user_addresses = addr_repo.list_by_user(current_user.id, limit=5)
    total_count = addr_repo.count_by_user(current_user.id)
    active_count = len([a for a in addr_repo.list_by_user(current_user.id, limit=1000) if a.is_active])
    
    # Calculate resolutions count for user's addresses
    user_addr_ids = {a.id for a in addr_repo.list_by_user(current_user.id, limit=1000)}
    user_resolutions = sum(len(a.access_logs) for a in user_addresses)

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context={
            "request": request,
            "current_user": current_user,
            "addresses": user_addresses,
            "total_count": total_count,
            "active_count": active_count,
            "user_resolutions": user_resolutions,
            "active_nav": "dashboard",
            "base_url": settings.PUBLIC_BASE_URL
        }
    )


@router.get("/my-addresses", response_class=HTMLResponse)
def my_addresses_page(
    request: Request,
    search: Optional[str] = None,
    address_type: Optional[str] = None,
    location_scope: Optional[str] = None,
    is_active: Optional[str] = None,
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    addr_repo = AddressRepository(db)
    
    active_bool = None
    if is_active == "true":
        active_bool = True
    elif is_active == "false":
        active_bool = False

    addresses = addr_repo.list_by_user(
        user_id=current_user.id,
        search=search,
        address_type=address_type,
        location_scope=location_scope,
        is_active=active_bool,
        limit=100
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/my_addresses.html",
        context={
            "request": request,
            "current_user": current_user,
            "addresses": addresses,
            "search": search,
            "address_type": address_type,
            "location_scope": location_scope,
            "is_active": active_bool,
            "active_nav": "my_addresses",
            "base_url": settings.PUBLIC_BASE_URL
        }
    )
