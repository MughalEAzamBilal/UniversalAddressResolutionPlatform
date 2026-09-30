from flask import Blueprint, render_template, request
from app.database.session import get_db
from app.web.deps import require_web_user, get_current_web_user
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.core.config import get_settings

dashboard_bp = Blueprint("dashboard", __name__)
settings = get_settings()


@dashboard_bp.route("/dashboard", methods=["GET"])
@require_web_user
def user_dashboard():
    db = get_db()
    current_user = get_current_web_user()
    addr_repo = AddressRepository(db)

    user_addresses = addr_repo.list_by_user(current_user.id, limit=5)
    total_count = addr_repo.count_by_user(current_user.id)
    all_user_addresses = addr_repo.list_by_user(current_user.id, limit=1000)
    active_count = len([a for a in all_user_addresses if a.is_active])
    user_resolutions = sum(len(a.access_logs) for a in user_addresses)

    return render_template(
        "dashboard/index.html",
        current_user=current_user,
        addresses=user_addresses,
        total_count=total_count,
        active_count=active_count,
        user_resolutions=user_resolutions,
        active_nav="dashboard",
        base_url=settings.PUBLIC_BASE_URL
    )


@dashboard_bp.route("/my-addresses", methods=["GET"])
@require_web_user
def my_addresses_page():
    db = get_db()
    current_user = get_current_web_user()
    addr_repo = AddressRepository(db)

    search = request.args.get("search")
    address_type = request.args.get("address_type")
    location_scope = request.args.get("location_scope")
    is_active = request.args.get("is_active")

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

    return render_template(
        "dashboard/my_addresses.html",
        current_user=current_user,
        addresses=addresses,
        search=search,
        address_type=address_type,
        location_scope=location_scope,
        is_active=active_bool,
        active_nav="my_addresses",
        base_url=settings.PUBLIC_BASE_URL
    )
