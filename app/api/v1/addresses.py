from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    AddressVersionResponse
)
from app.services.address_service import AddressService
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.core.exceptions import AppError

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new structured address.
    System generates a unique 6-character Public Address ID (LLDDYY).
    """
    service = AddressService(db)
    try:
        return service.create_address(user_id=current_user.id, data=data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("", response_model=List[AddressResponse])
def list_addresses(
    search: Optional[str] = None,
    address_type: Optional[str] = None,
    location_scope: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List addresses belonging to current authenticated user."""
    service = AddressService(db)
    return service.list_user_addresses(
        user_id=current_user.id,
        search=search,
        address_type=address_type,
        location_scope=location_scope,
        is_active=is_active,
        skip=skip,
        limit=limit
    )


@router.get("/{public_id}", response_model=AddressResponse)
def get_address(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve an address by Public Address ID for owner or admin."""
    service = AddressService(db)
    addr = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and addr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied.")
    return addr


@router.put("/{public_id}", response_model=AddressResponse)
def update_address(
    public_id: str,
    data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update address details.
    The 6-character Public Address ID remains permanently stable!
    Creates an address_versions snapshot.
    """
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    try:
        return service.update_address(
            public_id=public_id,
            user_id=current_user.id,
            data=data,
            is_admin=is_admin
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an address and its versions."""
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    try:
        service.delete_address(public_id, user_id=current_user.id, is_admin=is_admin)
        return None
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{public_id}/versions", response_model=List[AddressVersionResponse])
def get_address_versions(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View version snapshots of address modifications."""
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    try:
        return service.get_versions(public_id, user_id=current_user.id, is_admin=is_admin)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
