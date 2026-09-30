from flask import Blueprint, render_template, request, Response
from app.database.session import get_db
from app.services.resolver_service import ResolverService
from app.services.ad_service import AdService
from app.models.advertisement import AdPlacement
from app.web.deps import get_client_ip
from app.core.exceptions import AddressNotFoundError, AddressDeactivatedError, AddressPrivateError, AppError

resolver_bp = Blueprint("resolver", __name__)


@resolver_bp.route("/demo", methods=["GET"])
@resolver_bp.route("/a/demo", methods=["GET"])
def resolver_demo():
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
    return render_template("resolver/resolve.html", data=demo_data, ads=[])


@resolver_bp.route("/<public_id>", methods=["GET"])
@resolver_bp.route("/a/<public_id>", methods=["GET"])
def resolve_address_web(public_id: str):
    """
    Core Public Address Resolver Web Page.
    Resolves 6-character Public ID into physical address,
    triggers clipboard copy animation, and initiates redirect.
    """
    clean_id = public_id.strip().lower()
    if clean_id in ("favicon.ico", "robots.txt", "sitemap.xml"):
        return Response("", status=204 if clean_id == "favicon.ico" else 404)

    if len(clean_id) != 6 or not clean_id.isalnum():
        return render_template(
            "resolver/error.html",
            status_code=404,
            error_title="Address Not Found",
            error_message="The address link may be incorrect, expired, or does not exist.",
            public_id=clean_id
        ), 404

    db = get_db()
    ip = get_client_ip()
    ua = request.headers.get("User-Agent")
    referrer = request.headers.get("Referer")

    service = ResolverService(db)
    try:
        resolved = service.resolve(
            public_id=clean_id,
            ip_address=ip,
            user_agent=ua,
            referrer=referrer
        )
        ad_service = AdService(db)
        active_ads = ad_service.get_active_ads(placement=AdPlacement.BELOW_RESOLVER)
        for ad in active_ads:
            ad_service.record_impression(ad.id)

        return render_template(
            "resolver/resolve.html",
            data=resolved,
            ads=active_ads
        )
    except AddressNotFoundError:
        return render_template(
            "resolver/error.html",
            status_code=404,
            error_title="Address Not Found",
            error_message="The address link may be incorrect, expired, or does not exist.",
            public_id=clean_id
        ), 404
    except AddressDeactivatedError:
        return render_template(
            "resolver/error.html",
            status_code=410,
            error_title="Address Currently Unavailable",
            error_message="This smart address link has been paused or deactivated by its owner.",
            public_id=clean_id
        ), 410
    except AddressPrivateError:
        return render_template(
            "resolver/error.html",
            status_code=403,
            error_title="Address Is Private",
            error_message="This address is marked private and cannot be resolved publicly.",
            public_id=clean_id
        ), 403
    except AppError as e:
        return render_template(
            "resolver/error.html",
            status_code=e.status_code,
            error_title="Unable to Resolve",
            error_message=e.message,
            public_id=clean_id
        ), e.status_code
