from flask import Blueprint, render_template
from app.database.session import get_db
from app.web.deps import get_current_web_user
from app.core.config import get_settings
from app.services.ad_service import AdService
from app.models.advertisement import AdPlacement

home_bp = Blueprint("home", __name__)
settings = get_settings()


@home_bp.route("/", methods=["GET"])
def index():
    db = get_db()
    current_user = get_current_web_user()
    ad_service = AdService(db)
    home_ads = ad_service.get_active_ads(placement=AdPlacement.HOME_CONTENT)
    for ad in home_ads:
        ad_service.record_impression(ad.id)

    return render_template(
        "home.html",
        current_user=current_user,
        active_nav="home",
        base_url=settings.PUBLIC_BASE_URL,
        ads=home_ads
    )
