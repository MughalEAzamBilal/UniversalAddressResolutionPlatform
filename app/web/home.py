from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.web.deps import get_current_web_user
from app.core.config import get_settings
from starlette.templating import Jinja2Templates

from app.services.ad_service import AdService
from app.models.advertisement import AdPlacement

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    current_user=Depends(get_current_web_user),
    db: Session = Depends(get_db)
):
    ad_service = AdService(db)
    home_ads = ad_service.get_active_ads(placement=AdPlacement.HOME_CONTENT)
    for ad in home_ads:
        ad_service.record_impression(ad.id)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "current_user": current_user,
            "active_nav": "home",
            "base_url": settings.PUBLIC_BASE_URL,
            "ads": home_ads
        }
    )
