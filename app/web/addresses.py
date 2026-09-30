from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.web.deps import require_web_user, get_current_web_user
from app.api.deps import get_client_ip
from app.services.address_service import AddressService
from app.services.address_formatter import AddressFormatter
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.schemas.address import AddressCreate, AddressUpdate
from app.models.user import UserRole
from app.models.address import AddressType
from app.core.exceptions import AppError
from app.core.config import get_settings
from starlette.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/address/new", response_class=HTMLResponse)
@router.get("/create-edit-id", response_class=HTMLResponse)
def create_address_page(
    request: Request,
    welcome_edit_id: Optional[str] = None,
    current_user=Depends(get_current_web_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        from app.services.public_id_generator import public_id_generator
        preview_pub_id = public_id_generator.generate(db)
        return templates.TemplateResponse(
            request=request,
            name="address/create_edit_id.html",
            context={
                "request": request,
                "current_user": None,
                "preview_public_id": preview_pub_id,
                "active_nav": "new_address"
            }
        )
    return templates.TemplateResponse(
        request=request,
        name="address/new.html",
        context={
            "request": request,
            "current_user": current_user,
            "welcome_edit_id": welcome_edit_id,
            "active_nav": "new_address"
        }
    )


@router.post("/address/create-edit-id", response_class=HTMLResponse)
def create_edit_id_submit(
    request: Request,
    father_name: str = Form(...),
    mother_name: str = Form(...),
    cnic_or_id_card: str = Form(...),
    date_of_birth: str = Form(...),
    public_id: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    enable_phone: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        clean_cnic = "".join(filter(str.isdigit, cnic_or_id_card.strip()))
        if len(clean_cnic) > 3:
            raise AppError("CNIC ending must not exceed 3 digit numbers.", status_code=400)
        if len(clean_cnic) == 0:
            raise AppError("CNIC ending must contain numeric digits (maximum 3 digits, e.g. 123).", status_code=400)

        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        auth_service = AuthService(db)
        resolved_name = full_name.strip() if full_name and full_name.strip() else f"User {father_name.strip().upper()}{mother_name.strip().upper()}"
        resolved_phone = phone.strip() if (enable_phone and phone and phone.strip()) else None

        from app.models.address import Address
        from app.services.public_id_generator import public_id_generator
        clean_pub_id = public_id.strip()[:6].lower() if public_id and len(public_id.strip()) >= 6 else None
        if clean_pub_id:
            if db.query(Address).filter(Address.public_id == clean_pub_id).first():
                clean_pub_id = public_id_generator.generate(db)
        else:
            clean_pub_id = public_id_generator.generate(db)

        user, raw_edit_id = auth_service.register_or_get_by_edit_id(
            full_name=resolved_name,
            father_name=father_name,
            mother_name=mother_name,
            cnic_or_id_card=clean_cnic,
            date_of_birth=dob,
            phone=resolved_phone,
            email=email,
            public_id=clean_pub_id
        )

        token_data = auth_service.create_edit_session_token(user)

        response = RedirectResponse(url=f"/address/new?welcome_edit_id={raw_edit_id}", status_code=303)
        response.set_cookie(
            key="edit_session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except AppError as e:
        from app.services.public_id_generator import public_id_generator
        return templates.TemplateResponse(
            request=request,
            name="address/create_edit_id.html",
            context={"request": request, "error": e.message, "current_user": None, "preview_public_id": public_id_generator.generate(db), "active_nav": "new_address"},
            status_code=e.status_code
        )
    except Exception as e:
        from app.services.public_id_generator import public_id_generator
        return templates.TemplateResponse(
            request=request,
            name="address/create_edit_id.html",
            context={"request": request, "error": f"Please verify all fields: {str(e)}", "current_user": None, "preview_public_id": public_id_generator.generate(db), "active_nav": "new_address"},
            status_code=400
        )


@router.post("/address/use-existing-edit-id", response_class=HTMLResponse)
def use_existing_edit_id_submit(
    request: Request,
    edit_id: str = Form(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    try:
        user = EditIdService.verify_and_authenticate(db, edit_id, ip_address=ip)
        auth_service = AuthService(db)
        token_data = auth_service.create_edit_session_token(user)

        response = RedirectResponse(url="/address/new", status_code=303)
        response.set_cookie(
            key="edit_session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return response
    except AppError as e:
        return templates.TemplateResponse(
            request=request,
            name="address/create_edit_id.html",
            context={"request": request, "error": e.message, "current_user": None, "active_nav": "new_address"},
            status_code=e.status_code
        )



@router.post("/address/new", response_class=HTMLResponse)
def create_address_submit(
    request: Request,
    address_type: str = Form("PERSONAL"),
    location_scope: str = Form("LOCAL"),
    visibility: str = Form("PUBLIC"),
    recipient_name: Optional[str] = Form(None),
    business_name: Optional[str] = Form(None),
    country: str = Form("Pakistan"),
    country_code: str = Form("PK"),
    province_state: Optional[str] = Form(None),
    region_division: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    tehsil: Optional[str] = Form(None),
    city: str = Form(...),
    town: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    locality: Optional[str] = Form(None),
    street: Optional[str] = Form(None),
    road: Optional[str] = Form(None),
    house_number: Optional[str] = Form(None),
    building: Optional[str] = Form(None),
    floor: Optional[str] = Form(None),
    flat: Optional[str] = Form(None),
    landmark: Optional[str] = Form(None),
    postal_code: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    destination_url: Optional[str] = Form(None),
    redirect_seconds: int = Form(3),
    current_user=Depends(get_current_web_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/address/new", status_code=303)
    try:
        clean_recipient = recipient_name.strip() if recipient_name else ""
        if not clean_recipient:
            raise AppError("Contact person name is compulsory for all addresses.", status_code=400)

        clean_business = business_name.strip() if business_name else ""
        if address_type.upper() == AddressType.BUSINESS and not clean_business:
            raise AppError("Business / Company name is required for business addresses.", status_code=400)

        data = AddressCreate(
            address_type=address_type,
            location_scope=location_scope,
            visibility=visibility,
            recipient_name=clean_recipient,
            business_name=clean_business if clean_business else None,
            country=country,
            country_code=country_code,
            province_state=province_state,
            region_division=region_division,
            district=district,
            tehsil=tehsil,
            city=city,
            town=town,
            area=area,
            locality=locality,
            street=street,
            road=road,
            house_number=house_number,
            building=building,
            floor=floor,
            flat=flat,
            landmark=landmark,
            postal_code=postal_code,
            latitude=latitude,
            longitude=longitude,
            destination_url=destination_url if destination_url and destination_url.strip() else None,
            redirect_seconds=redirect_seconds
        )
        service = AddressService(db)
        address = service.create_address(user_id=current_user.id, data=data)
        return RedirectResponse(url=f"/address/{address.public_id}/view", status_code=303)
    except AppError as e:
        return templates.TemplateResponse(
            request=request,
            name="address/new.html",
            context={
                "request": request,
                "current_user": current_user,
                "error": e.message,
                "active_nav": "new_address"
            },
            status_code=e.status_code
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="address/new.html",
            context={
                "request": request,
                "current_user": current_user,
                "error": str(e),
                "active_nav": "new_address"
            },
            status_code=400
        )


@router.get("/address/{public_id}/view", response_class=HTMLResponse)
def view_address_page(
    public_id: str,
    request: Request,
    owner_transferred: Optional[str] = None,
    new_edit_id: Optional[str] = None,
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        return RedirectResponse(url="/my-addresses", status_code=303)

    formatted_views = AddressFormatter.format_all_views(address)
    versions = service.get_versions(public_id, user_id=current_user.id, is_admin=is_admin)

    return templates.TemplateResponse(
        request=request,
        name="address/view.html",
        context={
            "request": request,
            "current_user": current_user,
            "address": address,
            "formatted_views": formatted_views,
            "versions": versions,
            "base_url": settings.PUBLIC_BASE_URL,
            "owner_transferred": owner_transferred == "true",
            "new_edit_id": new_edit_id,
            "active_nav": "my_addresses"
        }
    )


@router.get("/address/{public_id}/edit", response_class=HTMLResponse)
def edit_address_page(
    public_id: str,
    request: Request,
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        return RedirectResponse(url="/my-addresses", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="address/edit.html",
        context={
            "request": request,
            "current_user": current_user,
            "address": address,
            "active_nav": "my_addresses"
        }
    )


@router.post("/address/{public_id}/edit", response_class=HTMLResponse)
def edit_address_submit(
    public_id: str,
    request: Request,
    address_type: str = Form("PERSONAL"),
    location_scope: str = Form("LOCAL"),
    recipient_name: Optional[str] = Form(None),
    business_name: Optional[str] = Form(None),
    country: str = Form(...),
    city: str = Form(...),
    house_number: Optional[str] = Form(None),
    street: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    landmark: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    destination_url: Optional[str] = Form(None),
    redirect_seconds: int = Form(3),
    is_active: str = Form("true"),
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    try:
        clean_recipient = recipient_name.strip() if recipient_name else ""
        if not clean_recipient:
            raise AppError("Contact person name is compulsory.", status_code=400)

        clean_business = business_name.strip() if business_name else ""
        if address_type.upper() == AddressType.BUSINESS and not clean_business:
            raise AppError("Business / Company name is required for business addresses.", status_code=400)

        update_data = AddressUpdate(
            address_type=address_type,
            location_scope=location_scope,
            recipient_name=clean_recipient,
            business_name=clean_business if clean_business else None,
            country=country,
            city=city,
            house_number=house_number,
            street=street,
            district=district,
            landmark=landmark,
            latitude=latitude,
            longitude=longitude,
            destination_url=destination_url if destination_url and destination_url.strip() else None,
            redirect_seconds=redirect_seconds,
            is_active=(is_active == "true")
        )
        service.update_address(
            public_id=public_id,
            user_id=current_user.id,
            data=update_data,
            is_admin=is_admin
        )
        return RedirectResponse(url=f"/address/{public_id}/view", status_code=303)
    except AppError as e:
        address = service.get_by_public_id(public_id)
        return templates.TemplateResponse(
            "address/edit.html",
            {
                "request": request,
                "current_user": current_user,
                "address": address,
                "error": e.message,
                "active_nav": "my_addresses"
            },
            status_code=e.status_code
        )


@router.post("/address/{public_id}/transfer-owner", response_class=HTMLResponse)
def transfer_business_owner_submit(
    public_id: str,
    request: Request,
    new_owner_name: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    cnic_or_id_card: str = Form(...),
    date_of_birth: str = Form(...),
    current_user=Depends(require_web_user),
    db: Session = Depends(get_db)
):
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        raise AppError("Permission denied: You do not own this address.", status_code=403)

    if address.address_type != AddressType.BUSINESS:
        raise AppError("Owner transfer is strictly permitted for Business Addresses only.", status_code=400)

    clean_name = new_owner_name.strip()
    if not clean_name:
        raise AppError("New owner contact person name is compulsory.", status_code=400)

    clean_cnic = "".join(filter(str.isdigit, cnic_or_id_card.strip()))
    if len(clean_cnic) > 3 or len(clean_cnic) == 0:
        raise AppError("CNIC ending must be between 1 and 3 numeric digits (e.g. 123).", status_code=400)

    try:
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except Exception:
        raise AppError("Invalid date of birth format. Please use YYYY-MM-DD.", status_code=400)

    # Generate new unique 13-character Edit ID for the new business owner
    new_raw_edit_id = EditIdService.generate_unique_edit_id(
        db=db,
        public_id=address.public_id,
        father_name=father_name,
        mother_name=mother_name,
        cnic_or_id_card=clean_cnic,
        date_of_birth=dob,
        exclude_user_id=address.user_id
    )

    from app.core.security import normalize_edit_id, hash_edit_id
    from app.models.user import User
    from app.models.address_version import AddressVersion

    user = db.query(User).filter(User.id == address.user_id).first()
    if user:
        user.full_name = clean_name
        user.father_name = father_name.strip()
        user.mother_name = mother_name.strip()
        user.cnic_or_id_card = clean_cnic
        user.date_of_birth = dob
        user.edit_id_hash = hash_edit_id(normalize_edit_id(new_raw_edit_id))

    address.recipient_name = clean_name
    address.address_text = AddressFormatter.format_full(address)
    db.commit()
    db.refresh(address)

    # Record snapshot in address_versions
    snapshot_json = service._serialize_address_snapshot(address)
    existing_versions = service.repo.get_versions(address.id)
    next_ver = (existing_versions[0].version_number + 1) if existing_versions else 1
    new_version = AddressVersion(
        address_id=address.id,
        version_number=next_ver,
        address_snapshot=snapshot_json,
        changed_by=user.id if user else address.user_id
    )
    service.repo.create_version(new_version)

    auth_service = AuthService(db)
    token_data = auth_service.create_edit_session_token(user)

    response = RedirectResponse(
        url=f"/address/{public_id}/view?owner_transferred=true&new_edit_id={new_raw_edit_id}",
        status_code=303
    )
    response.set_cookie(
        key="edit_session_token",
        value=token_data["access_token"],
        httponly=True,
        max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return response
