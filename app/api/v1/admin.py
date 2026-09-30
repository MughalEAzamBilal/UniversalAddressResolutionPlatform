import os
import shutil
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.session import get_db, settings
from app.api.deps import get_current_admin, get_current_staff
from app.models.user import User, UserRole, AccountStatus
from app.models.address import Address
from app.repositories.user_repository import UserRepository
from app.repositories.address_repository import AddressRepository
from app.repositories.log_repository import LogRepository
from app.services.audit_service import AuditService
from app.services.public_id_generator import public_id_generator
from app.services.address_service import AddressService
from app.services.edit_id_service import EditIdService
from app.core.security import hash_password, hash_edit_id
from app.schemas.admin import (
    AdminDashboardStats,
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset,
    AdminEditIdReset,
    AccessLogResponse,
    AdminActionResponse,
)
from app.schemas.user import UserDetailResponse
from app.schemas.address import AddressResponse, AddressUpdate
from app.core.exceptions import AppError

router = APIRouter(prefix="/admin", tags=["Admin Operations"])


@router.get("/dashboard", response_model=AdminDashboardStats)
def get_dashboard_stats(
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    """Retrieve comprehensive platform metrics for administrative dashboard."""
    user_repo = UserRepository(db)
    addr_repo = AddressRepository(db)
    log_repo = LogRepository(db)

    addr_stats = addr_repo.get_stats()
    res_stats = log_repo.get_resolution_stats()

    return AdminDashboardStats(
        total_users=user_repo.count_users(),
        total_addresses=addr_stats["total_addresses"],
        active_addresses=addr_stats["active_addresses"],
        inactive_addresses=addr_stats["inactive_addresses"],
        local_addresses=addr_stats["local_addresses"],
        international_addresses=addr_stats["international_addresses"],
        today_resolutions=res_stats["today_resolutions"],
        failed_resolutions=res_stats["failed_resolutions"],
    )


@router.get("/generator-status")
def get_generator_status(
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
    year: Optional[int] = None
):
    """Capacity and status metrics for Public Address ID pattern stages."""
    current_year = year or datetime.now(timezone.utc).year
    stats = public_id_generator.get_pattern_statistics(db, current_year)
    return {
        "year": current_year,
        "patterns": stats
    }


@router.get("/users", response_model=List[UserDetailResponse])
def list_users(
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List and search users."""
    user_repo = UserRepository(db)
    return user_repo.list_users(skip=skip, limit=limit, search=search)


@router.post("/users", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
def create_user_as_admin(
    req: AdminUserCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint to create a user account."""
    user_repo = UserRepository(db)
    if user_repo.get_by_username(req.username):
        raise HTTPException(status_code=409, detail="Username already exists.")
    if user_repo.get_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already exists.")

    dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
    edit_id = EditIdService.generate_edit_id(req.father_name, req.mother_name, req.cnic_or_id_card, dob)

    user = User(
        username=req.username.strip(),
        email=req.email.strip().lower(),
        phone=req.phone.strip() if req.phone else None,
        full_name=req.full_name.strip(),
        father_name=req.father_name.strip(),
        mother_name=req.mother_name.strip(),
        cnic_or_id_card=req.cnic_or_id_card.strip(),
        date_of_birth=dob,
        password_hash=hash_password(req.password),
        edit_id_hash=hash_edit_id(edit_id),
        role=req.role.upper(),
        account_status=AccountStatus.ACTIVE
    )
    created = user_repo.create(user)

    audit = AuditService(db)
    audit.log_action(
        admin_user_id=admin.id,
        action="CREATE_USER",
        target_type="USER",
        target_id=str(created.id),
        details=f"Created user {created.username} with role {created.role}"
    )
    return created


@router.put("/users/{user_id}", response_model=UserDetailResponse)
def update_user_as_admin(
    user_id: int,
    req: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if req.full_name:
        user.full_name = req.full_name.strip()
    if req.phone is not None:
        user.phone = req.phone.strip() if req.phone else None
    if req.role:
        user.role = req.role.upper()
    if req.account_status:
        user.account_status = req.account_status.upper()
        if user.account_status == AccountStatus.ACTIVE:
            user.failed_login_attempts = 0
            user.locked_until = None

    user.updated_at = datetime.now(timezone.utc)
    updated = user_repo.update(user)

    audit = AuditService(db)
    audit.log_action(
        admin_user_id=admin.id,
        action="UPDATE_USER",
        target_type="USER",
        target_id=str(user.id),
        details=f"Updated user status={user.account_status}, role={user.role}"
    )
    return updated


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    req: AdminPasswordReset,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(req.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.updated_at = datetime.now(timezone.utc)
    user_repo.update(user)

    audit = AuditService(db)
    audit.log_action(
        admin_user_id=admin.id,
        action="RESET_PASSWORD",
        target_type="USER",
        target_id=str(user.id),
        details=f"Reset password for {user.username}"
    )
    return {"message": f"Password reset successfully for user {user.username}"}


@router.post("/users/{user_id}/reset-edit-id")
def reset_edit_id(
    user_id: int,
    req: AdminEditIdReset,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
    new_edit_id = EditIdService.generate_edit_id(req.father_name, req.mother_name, req.cnic_or_id_card, dob)

    user.father_name = req.father_name.strip()
    user.mother_name = req.mother_name.strip()
    user.cnic_or_id_card = req.cnic_or_id_card.strip()
    user.date_of_birth = dob
    user.edit_id_hash = hash_edit_id(new_edit_id)
    user.updated_at = datetime.now(timezone.utc)
    user_repo.update(user)

    audit = AuditService(db)
    audit.log_action(
        admin_user_id=admin.id,
        action="RESET_EDIT_ID",
        target_type="USER",
        target_id=str(user.id),
        details=f"Reset Edit ID for {user.username}"
    )
    return {
        "message": f"Edit ID regenerated for {user.username}",
        "new_edit_id": new_edit_id
    }


@router.get("/addresses", response_model=List[AddressResponse])
def list_all_addresses(
    search: Optional[str] = None,
    city: Optional[str] = None,
    country: Optional[str] = None,
    address_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    addr_repo = AddressRepository(db)
    return addr_repo.list_all(
        search=search,
        city=city,
        country=country,
        address_type=address_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )


@router.post("/addresses/{public_id}/toggle-status")
def toggle_address_status(
    public_id: str,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
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
    return {"public_id": public_id, "is_active": new_status}


@router.get("/logs", response_model=List[AccessLogResponse])
def list_access_logs(
    search: Optional[str] = None,
    success: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db)
):
    log_repo = LogRepository(db)
    return log_repo.list_access_logs(skip=skip, limit=limit, search=search, success=success)


@router.get("/backup")
def backup_database(
    admin: User = Depends(get_current_admin)
):
    """
    Safely backup the SQLite database using SQLite's backup API.
    Guarantees consistent, non-corrupted database file.
    """
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        raise HTTPException(status_code=400, detail="Automated backup only supported for SQLite in V1.")

    src_path = db_url.replace("sqlite:///", "")
    if not os.path.exists(src_path):
        raise HTTPException(status_code=404, detail="Database file does not exist yet.")

    backups_dir = os.path.join(os.path.dirname(src_path), "backups")
    os.makedirs(backups_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_path = os.path.join(backups_dir, f"backup_{timestamp}.db")

    # Use SQLite online backup API
    src_conn = sqlite3.connect(src_path)
    dest_conn = sqlite3.connect(dest_path)
    with dest_conn:
        src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()

    return {
        "message": "Database backup completed successfully.",
        "backup_file": dest_path,
        "timestamp": timestamp
    }
