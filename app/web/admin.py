import os
import sqlite3
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect
from app.database.session import get_db
from app.core.config import get_settings
from app.web.deps import require_web_admin, get_current_web_user
from app.repositories.user_repository import UserRepository
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.services.public_id_generator import public_id_generator
from app.services.address_service import AddressService
from app.services.audit_service import AuditService
from app.services.ad_service import AdService
from app.models.advertisement import AdPlacement, AdType
from app.models.user import AccountStatus

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
settings = get_settings()


@admin_bp.route("", methods=["GET"])
@require_web_admin
def admin_dashboard():
    db = get_db()
    current_user = get_current_web_user()
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

    return render_template(
        "admin/dashboard.html",
        current_user=current_user,
        stats=stats,
        active_nav="admin_dashboard"
    )


@admin_bp.route("/users", methods=["GET"])
@require_web_admin
def admin_users_page():
    db = get_db()
    current_user = get_current_web_user()
    user_repo = UserRepository(db)
    search = request.args.get("search")
    users = user_repo.list_users(search=search, limit=100)
    return render_template(
        "admin/users.html",
        current_user=current_user,
        users=users,
        search=search,
        active_nav="admin_users"
    )


@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@require_web_admin
def admin_toggle_user_status(user_id: int):
    db = get_db()
    current_user = get_current_web_user()
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if user:
        user.account_status = AccountStatus.INACTIVE if user.account_status == AccountStatus.ACTIVE else AccountStatus.ACTIVE
        user_repo.update(user)
        audit = AuditService(db)
        audit.log_action(current_user.id, "TOGGLE_USER_STATUS", "USER", str(user.id), f"Set to {user.account_status}")
    return redirect("/admin/users", code=303)


@admin_bp.route("/addresses", methods=["GET"])
@require_web_admin
def admin_addresses_page():
    db = get_db()
    current_user = get_current_web_user()
    addr_repo = AddressRepository(db)
    search = request.args.get("search")
    city = request.args.get("city")
    country = request.args.get("country")
    addresses = addr_repo.list_all(search=search, city=city, country=country, limit=100)
    return render_template(
        "admin/addresses.html",
        current_user=current_user,
        addresses=addresses,
        search=search,
        city=city,
        country=country,
        active_nav="admin_addresses"
    )


@admin_bp.route("/addresses/<public_id>/toggle-status", methods=["POST"])
@require_web_admin
def admin_toggle_address_status(public_id: str):
    db = get_db()
    current_user = get_current_web_user()
    service = AddressService(db)
    addr = service.get_by_public_id(public_id)
    if addr:
        service.set_active_status(public_id, user_id=current_user.id, is_active=not addr.is_active, is_admin=True)
        audit = AuditService(db)
        audit.log_action(current_user.id, "TOGGLE_ADDRESS_STATUS", "ADDRESS", public_id, f"Set to {not addr.is_active}")

    referrer = request.headers.get("Referer", "/admin/addresses")
    return redirect(referrer, code=303)


@admin_bp.route("/links", methods=["GET"])
@require_web_admin
def admin_links_page():
    db = get_db()
    current_user = get_current_web_user()
    addr_repo = AddressRepository(db)
    addresses = addr_repo.list_all(limit=100)
    return render_template(
        "admin/links.html",
        current_user=current_user,
        addresses=addresses,
        base_url=settings.PUBLIC_BASE_URL,
        active_nav="admin_links"
    )


@admin_bp.route("/generator", methods=["GET"])
@require_web_admin
def admin_generator_page():
    db = get_db()
    current_user = get_current_web_user()
    year = datetime.now(timezone.utc).year
    stats = public_id_generator.get_pattern_statistics(db, year)
    return render_template(
        "admin/generator.html",
        current_user=current_user,
        year=year,
        patterns=stats,
        active_nav="admin_generator"
    )


@admin_bp.route("/logs", methods=["GET"])
@require_web_admin
def admin_logs_page():
    db = get_db()
    current_user = get_current_web_user()
    log_repo = LogRepository(db)
    search = request.args.get("search")
    logs = log_repo.list_access_logs(search=search, limit=100)
    return render_template(
        "admin/logs.html",
        current_user=current_user,
        logs=logs,
        search=search,
        active_nav="admin_logs"
    )

def _get_sqlite_paths():
    db_url = settings.DATABASE_URL
    rel_path = db_url.replace("sqlite:///", "")
    if os.path.isabs(rel_path):
        src_path = rel_path
    else:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        src_path = os.path.normpath(os.path.join(project_root, rel_path))
    backups_dir = os.path.join(os.path.dirname(src_path), "backups")
    return src_path, backups_dir


@admin_bp.route("/system/backup", methods=["GET"])
@require_web_admin
def admin_backup_database():
    src_path, backups_dir = _get_sqlite_paths()
    if os.path.exists(src_path):
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.abspath(os.path.join(backups_dir, f"backup_{timestamp}.db"))
        
        src_conn = sqlite3.connect(src_path)
        dest_conn = sqlite3.connect(dest_path)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()
        src_conn.close()

        if request.args.get("download") == "true":
            from flask import send_file
            return send_file(
                dest_path,
                as_attachment=True,
                download_name=f"address_platform_backup_{timestamp}.db"
            )

    return redirect("/admin?backup=success", code=303)


@admin_bp.route("/system/backup/download", methods=["GET"])
@require_web_admin
def admin_download_backup():
    src_path, backups_dir = _get_sqlite_paths()
    if not os.path.exists(src_path):
        from flask import abort
        abort(404)

    os.makedirs(backups_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.abspath(os.path.join(backups_dir, f"backup_{timestamp}.db"))

    src_conn = sqlite3.connect(src_path)
    dest_conn = sqlite3.connect(dest_path)
    with dest_conn:
        src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()

    from flask import send_file
    return send_file(
        dest_path,
        as_attachment=True,
        download_name=f"address_platform_backup_{timestamp}.db"
    )


@admin_bp.route("/ads", methods=["GET"])
@require_web_admin
def admin_ads_page():
    db = get_db()
    current_user = get_current_web_user()
    ad_service = AdService(db)
    ads = ad_service.get_all_ads()
    stats = ad_service.get_stats()
    return render_template(
        "admin/ads.html",
        current_user=current_user,
        ads=ads,
        stats=stats,
        placements=AdPlacement.ALL,
        types=AdType.ALL,
        active_nav="admin_ads"
    )


@admin_bp.route("/ads/create", methods=["POST"])
@require_web_admin
def admin_create_ad():
    db = get_db()
    ad_service = AdService(db)
    ad_service.create_ad(
        title=request.form.get("title", ""),
        placement=request.form.get("placement", ""),
        ad_type=request.form.get("ad_type", AdType.GOOGLE_ADSENSE),
        code_snippet=request.form.get("code_snippet"),
        image_url=request.form.get("image_url"),
        target_url=request.form.get("target_url"),
        display_order=int(request.form.get("display_order", 0) or 0)
    )
    return redirect("/admin/ads?success=created", code=303)


@admin_bp.route("/ads/<int:ad_id>/toggle", methods=["POST"])
@require_web_admin
def admin_toggle_ad(ad_id: int):
    db = get_db()
    ad_service = AdService(db)
    ad_service.toggle_active(ad_id)
    return redirect("/admin/ads?success=toggled", code=303)


@admin_bp.route("/ads/<int:ad_id>/delete", methods=["POST"])
@require_web_admin
def admin_delete_ad(ad_id: int):
    db = get_db()
    ad_service = AdService(db)
    ad_service.delete_ad(ad_id)
    return redirect("/admin/ads?success=deleted", code=303)
