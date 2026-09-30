import os
import sqlite3
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.database.session import get_db
from app.core.config import get_settings
from app.api.deps import get_api_admin
from app.models.user import User, AccountStatus
from app.repositories.user_repository import UserRepository
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.services.audit_service import AuditService
from app.services.public_id_generator import public_id_generator
from app.services.address_service import AddressService
from app.services.edit_id_service import EditIdService
from app.core.security import hash_password, hash_edit_id
from app.schemas.address import AddressResponse

admin_api_bp = Blueprint("api_admin", __name__)
settings = get_settings()


@admin_api_bp.route("/admin/dashboard", methods=["GET"])
def get_dashboard_stats():
    admin = get_api_admin()
    db = get_db()
    user_repo = UserRepository(db)
    addr_repo = AddressRepository(db)
    log_repo = LogRepository(db)

    addr_stats = addr_repo.get_stats()
    res_stats = log_repo.get_resolution_stats()

    return jsonify({
        "total_users": user_repo.count_users(),
        "total_addresses": addr_stats["total_addresses"],
        "active_addresses": addr_stats["active_addresses"],
        "inactive_addresses": addr_stats["inactive_addresses"],
        "local_addresses": addr_stats["local_addresses"],
        "international_addresses": addr_stats["international_addresses"],
        "today_resolutions": res_stats["today_resolutions"],
        "failed_resolutions": res_stats["failed_resolutions"],
    })


@admin_api_bp.route("/admin/generator-status", methods=["GET"])
def get_generator_status():
    admin = get_api_admin()
    db = get_db()
    year = int(request.args.get("year", datetime.now(timezone.utc).year))
    stats = public_id_generator.get_pattern_statistics(db, year)
    return jsonify({
        "year": year,
        "patterns": stats
    })


@admin_api_bp.route("/admin/addresses", methods=["GET"])
def list_all_addresses():
    admin = get_api_admin()
    db = get_db()
    addr_repo = AddressRepository(db)
    search = request.args.get("search")
    city = request.args.get("city")
    country = request.args.get("country")
    address_type = request.args.get("address_type")
    is_active = request.args.get("is_active")
    active_bool = None
    if is_active == "true":
        active_bool = True
    elif is_active == "false":
        active_bool = False

    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 50))

    addresses = addr_repo.list_all(
        search=search,
        city=city,
        country=country,
        address_type=address_type,
        is_active=active_bool,
        skip=skip,
        limit=limit
    )
    return jsonify([AddressResponse.model_validate(a).model_dump() for a in addresses])


@admin_api_bp.route("/admin/addresses/<public_id>/toggle-status", methods=["POST"])
def toggle_address_status(public_id: str):
    admin = get_api_admin()
    db = get_db()
    service = AddressService(db)
    addr = service.get_by_public_id(public_id)
    new_status = not addr.is_active
    service.set_active_status(public_id, user_id=admin.id, is_active=new_status, is_admin=True)

    audit = AuditService(db)
    audit.log_action(
        admin_user_id=admin.id,
        action="TOGGLE_ADDRESS_STATUS",
        target_type="ADDRESS",
        target_id=public_id,
        details=f"Address {public_id} active set to {new_status}"
    )
    return jsonify({"public_id": public_id, "is_active": new_status})


@admin_api_bp.route("/admin/backup", methods=["GET"])
def backup_database():
    admin = get_api_admin()
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        return jsonify({"detail": "Automated backup only supported for SQLite."}), 400

    src_path = db_url.replace("sqlite:///", "")
    if not os.path.exists(src_path):
        return jsonify({"detail": "Database file does not exist yet."}), 404

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

    return jsonify({
        "message": "Database backup completed successfully.",
        "backup_file": dest_path,
        "timestamp": timestamp
    })
