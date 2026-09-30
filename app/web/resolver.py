from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.resolver_service import ResolverService
from app.api.deps import get_client_ip
from app.core.exceptions import AddressNotFoundError, AddressDeactivatedError, AddressPrivateError, AppError
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/demo", response_class=HTMLResponse)
@router.get("/a/demo", response_class=HTMLResponse)
def resolver_demo(request: Request):
    """Interactive demo of public address resolver with countdown and clipboard."""
    demo_data = {
        "public_id": "ab1226",
        "address_type": "DELIVERY",
        "display_text": "House 25, Street 4, Near Main Market, Taunsa Sharif, Dera Ghazi Khan, Punjab, Pakistan",
        "city": "Taunsa Sharif",
        "country": "Pakistan",
        "destination_url": "https://maps.google.com",
        "driving_directions_url": "https://www.google.com/maps/dir/?api=1&destination=30.7031,70.6500&travelmode=driving",
        "redirect_seconds": 3
    }
    return templates.TemplateResponse(
        request=request,
        name="resolver/resolve.html",
        context={
            "request": request,
            "data": demo_data
        }
    )


@router.get("/{public_id}", response_class=HTMLResponse)
@router.get("/a/{public_id}", response_class=HTMLResponse)
def resolve_address_web(
    public_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Core Public Address Resolver Web Page.
    Resolves 6-character Public ID into physical address,
    triggers clipboard copy animation, and initiates redirect.
    """
    clean_id = public_id.strip().lower()
    if clean_id in ("favicon.ico", "robots.txt", "sitemap.xml"):
        return Response(status_code=404)
    if len(clean_id) != 6 or not clean_id.isalnum():
        raise AddressNotFoundError(f"Address identifier '{public_id}' is invalid or does not exist.")
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    service = ResolverService(db)
    try:
        resolved = service.resolve(
            public_id=clean_id,
            ip_address=ip,
            user_agent=ua,
            referrer=referrer
        )
        from app.services.ad_service import AdService
        from app.models.advertisement import AdPlacement
        ad_service = AdService(db)
        active_ads = ad_service.get_active_ads(placement=AdPlacement.BELOW_RESOLVER)
        for ad in active_ads:
            ad_service.record_impression(ad.id)

        return templates.TemplateResponse(
            request=request,
            name="resolver/resolve.html",
            context={
                "request": request,
                "data": resolved,
                "ads": active_ads
            }
        )
    except AddressNotFoundError as e:
        return templates.TemplateResponse(
            request=request,
            name="resolver/error.html",
            context={
                "request": request,
                "status_code": 404,
                "error_title": "Address Not Found",
                "error_message": "The address link may be incorrect, expired, or does not exist.",
                "public_id": clean_id
            },
            status_code=404
        )
    except AddressDeactivatedError as e:
        return templates.TemplateResponse(
            request=request,
            name="resolver/error.html",
            context={
                "request": request,
                "status_code": 410,
                "error_title": "Address Currently Unavailable",
                "error_message": "This smart address link has been paused or deactivated by its owner.",
                "public_id": clean_id
            },
            status_code=410
        )
    except AddressPrivateError as e:
        return templates.TemplateResponse(
            request=request,
            name="resolver/error.html",
            context={
                "request": request,
                "status_code": 403,
                "error_title": "Address Is Private",
                "error_message": "This address is marked private and cannot be resolved publicly.",
                "public_id": clean_id
            },
            status_code=403
        )
    except AppError as e:
        return templates.TemplateResponse(
            request=request,
            name="resolver/error.html",
            context={
                "request": request,
                "status_code": e.status_code,
                "error_title": "Unable to Resolve",
                "error_message": e.message,
                "public_id": clean_id
            },
            status_code=e.status_code
        )
