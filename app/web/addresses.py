from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, make_response
from app.database.session import get_db
from app.web.deps import require_web_user, get_current_web_user, get_client_ip
from app.services.address_service import AddressService
from app.services.address_formatter import AddressFormatter
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.schemas.address import AddressCreate, AddressUpdate
from app.models.user import UserRole
from app.models.address import AddressType
from app.core.exceptions import AppError
from app.core.config import get_settings

addresses_bp = Blueprint("addresses", __name__)
settings = get_settings()


@addresses_bp.route("/address/new", methods=["GET"])
@addresses_bp.route("/create-edit-id", methods=["GET"])
def create_address_page():
    db = get_db()
    current_user = get_current_web_user()
    welcome_edit_id = request.args.get("welcome_edit_id")

    if not current_user:
        from app.services.public_id_generator import public_id_generator
        preview_pub_id = public_id_generator.generate(db)
        return render_template(
            "address/create_edit_id.html",
            current_user=None,
            preview_public_id=preview_pub_id,
            active_nav="new_address"
        )
    return render_template(
        "address/new.html",
        current_user=current_user,
        welcome_edit_id=welcome_edit_id,
        active_nav="new_address"
    )


@addresses_bp.route("/address/create-edit-id", methods=["POST"])
def create_edit_id_submit():
    db = get_db()
    father_name = request.form.get("father_name", "").strip()
    mother_name = request.form.get("mother_name", "").strip()
    cnic_or_id_card = request.form.get("cnic_or_id_card", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip()
    public_id = request.form.get("public_id")
    full_name = request.form.get("full_name")
    enable_phone = request.form.get("enable_phone")
    phone = request.form.get("phone")
    email = request.form.get("email")

    try:
        clean_cnic = "".join(filter(str.isdigit, cnic_or_id_card))
        if len(clean_cnic) > 3:
            raise AppError("CNIC ending must not exceed 3 digit numbers.", status_code=400)
        if len(clean_cnic) == 0:
            raise AppError("CNIC ending must contain numeric digits (maximum 3 digits, e.g. 123).", status_code=400)

        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        auth_service = AuthService(db)
        resolved_name = full_name.strip() if full_name and full_name.strip() else f"User {father_name.upper()}{mother_name.upper()}"
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
        session["user_id"] = user.id

        response = make_response(redirect(f"/address/new?welcome_edit_id={raw_edit_id}", code=303))
        response.set_cookie(
            key="edit_session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            samesite="Lax"
        )
        return response
    except AppError as e:
        from app.services.public_id_generator import public_id_generator
        return render_template(
            "address/create_edit_id.html",
            error=e.message,
            current_user=None,
            preview_public_id=public_id_generator.generate(db),
            active_nav="new_address"
        ), e.status_code
    except Exception as e:
        from app.services.public_id_generator import public_id_generator
        return render_template(
            "address/create_edit_id.html",
            error=f"Please verify all fields: {str(e)}",
            current_user=None,
            preview_public_id=public_id_generator.generate(db),
            active_nav="new_address"
        ), 400


@addresses_bp.route("/address/use-existing-edit-id", methods=["POST"])
def use_existing_edit_id_submit():
    db = get_db()
    ip = get_client_ip()
    edit_id = request.form.get("edit_id", "").strip()

    try:
        user = EditIdService.verify_and_authenticate(db, edit_id, ip_address=ip)
        auth_service = AuthService(db)
        token_data = auth_service.create_edit_session_token(user)
        session["user_id"] = user.id

        response = make_response(redirect("/address/new", code=303))
        response.set_cookie(
            key="edit_session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
            samesite="Lax"
        )
        return response
    except AppError as e:
        return render_template(
            "address/create_edit_id.html",
            error=e.message,
            current_user=None,
            active_nav="new_address"
        ), e.status_code


@addresses_bp.route("/address/new", methods=["POST"])
def create_address_submit():
    current_user = get_current_web_user()
    if not current_user:
        return redirect("/address/new", code=303)

    db = get_db()
    form = request.form
    address_type = form.get("address_type", "PERSONAL")
    location_scope = form.get("location_scope", "LOCAL")
    visibility = form.get("visibility", "PUBLIC")
    recipient_name = form.get("recipient_name", "").strip()
    business_name = form.get("business_name", "").strip()

    try:
        if not recipient_name:
            raise AppError("Contact person name is compulsory for all addresses.", status_code=400)

        if address_type.upper() == AddressType.BUSINESS and not business_name:
            raise AppError("Business / Company name is required for business addresses.", status_code=400)

        lat = float(form.get("latitude")) if form.get("latitude") and form.get("latitude").strip() else None
        lng = float(form.get("longitude")) if form.get("longitude") and form.get("longitude").strip() else None
        redir_sec = int(form.get("redirect_seconds", 3) or 3)

        data = AddressCreate(
            address_type=address_type,
            location_scope=location_scope,
            visibility=visibility,
            recipient_name=recipient_name,
            business_name=business_name if business_name else None,
            country=form.get("country", "Pakistan"),
            country_code=form.get("country_code", "PK"),
            province_state=form.get("province_state"),
            region_division=form.get("region_division"),
            district=form.get("district"),
            tehsil=form.get("tehsil"),
            city=form.get("city", ""),
            town=form.get("town"),
            area=form.get("area"),
            locality=form.get("locality"),
            street=form.get("street"),
            road=form.get("road"),
            house_number=form.get("house_number"),
            building=form.get("building"),
            floor=form.get("floor"),
            flat=form.get("flat"),
            landmark=form.get("landmark"),
            postal_code=form.get("postal_code"),
            latitude=lat,
            longitude=lng,
            destination_url=form.get("destination_url") if form.get("destination_url", "").strip() else None,
            redirect_seconds=redir_sec
        )
        service = AddressService(db)
        address = service.create_address(user_id=current_user.id, data=data)
        return redirect(f"/address/{address.public_id}/view", code=303)
    except AppError as e:
        return render_template(
            "address/new.html",
            current_user=current_user,
            error=e.message,
            active_nav="new_address"
        ), e.status_code
    except Exception as e:
        return render_template(
            "address/new.html",
            current_user=current_user,
            error=str(e),
            active_nav="new_address"
        ), 400


@addresses_bp.route("/address/<public_id>/view", methods=["GET"])
@require_web_user
def view_address_page(public_id: str):
    db = get_db()
    current_user = get_current_web_user()
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        return redirect("/my-addresses", code=303)

    formatted_views = AddressFormatter.format_all_views(address)
    versions = service.get_versions(public_id, user_id=current_user.id, is_admin=is_admin)

    owner_transferred = request.args.get("owner_transferred") == "true"
    new_edit_id = request.args.get("new_edit_id")

    return render_template(
        "address/view.html",
        current_user=current_user,
        address=address,
        formatted_views=formatted_views,
        versions=versions,
        base_url=settings.PUBLIC_BASE_URL,
        owner_transferred=owner_transferred,
        new_edit_id=new_edit_id,
        active_nav="my_addresses"
    )


@addresses_bp.route("/address/<public_id>/edit", methods=["GET"])
@require_web_user
def edit_address_page(public_id: str):
    db = get_db()
    current_user = get_current_web_user()
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        return redirect("/my-addresses", code=303)

    return render_template(
        "address/edit.html",
        current_user=current_user,
        address=address,
        active_nav="my_addresses"
    )


@addresses_bp.route("/address/<public_id>/edit", methods=["POST"])
@require_web_user
def edit_address_submit(public_id: str):
    db = get_db()
    current_user = get_current_web_user()
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    form = request.form

    try:
        recipient_name = form.get("recipient_name", "").strip()
        if not recipient_name:
            raise AppError("Contact person name is compulsory.", status_code=400)

        address_type = form.get("address_type", "PERSONAL")
        business_name = form.get("business_name", "").strip()
        if address_type.upper() == AddressType.BUSINESS and not business_name:
            raise AppError("Business / Company name is required for business addresses.", status_code=400)

        lat = float(form.get("latitude")) if form.get("latitude") and form.get("latitude").strip() else None
        lng = float(form.get("longitude")) if form.get("longitude") and form.get("longitude").strip() else None
        redir_sec = int(form.get("redirect_seconds", 3) or 3)
        is_active = form.get("is_active", "true") == "true"

        update_data = AddressUpdate(
            address_type=address_type,
            location_scope=form.get("location_scope", "LOCAL"),
            recipient_name=recipient_name,
            business_name=business_name if business_name else None,
            country=form.get("country", ""),
            city=form.get("city", ""),
            house_number=form.get("house_number"),
            street=form.get("street"),
            district=form.get("district"),
            landmark=form.get("landmark"),
            latitude=lat,
            longitude=lng,
            destination_url=form.get("destination_url") if form.get("destination_url", "").strip() else None,
            redirect_seconds=redir_sec,
            is_active=is_active
        )
        service.update_address(
            public_id=public_id,
            user_id=current_user.id,
            data=update_data,
            is_admin=is_admin
        )
        return redirect(f"/address/{public_id}/view", code=303)
    except AppError as e:
        address = service.get_by_public_id(public_id)
        return render_template(
            "address/edit.html",
            current_user=current_user,
            address=address,
            error=e.message,
            active_nav="my_addresses"
        ), e.status_code


@addresses_bp.route("/address/<public_id>/transfer-owner", methods=["POST"])
@require_web_user
def transfer_business_owner_submit(public_id: str):
    db = get_db()
    current_user = get_current_web_user()
    service = AddressService(db)
    address = service.get_by_public_id(public_id)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    if not is_admin and address.user_id != current_user.id:
        raise AppError("Permission denied: You do not own this address.", status_code=403)

    if address.address_type != AddressType.BUSINESS:
        raise AppError("Owner transfer is strictly permitted for Business Addresses only.", status_code=400)

    form = request.form
    new_owner_name = form.get("new_owner_name", "").strip()
    father_name = form.get("father_name", "").strip()
    mother_name = form.get("mother_name", "").strip()
    cnic_or_id_card = form.get("cnic_or_id_card", "").strip()
    date_of_birth = form.get("date_of_birth", "").strip()

    if not new_owner_name:
        raise AppError("New owner contact person name is compulsory.", status_code=400)

    clean_cnic = "".join(filter(str.isdigit, cnic_or_id_card))
    if len(clean_cnic) > 3 or len(clean_cnic) == 0:
        raise AppError("CNIC ending must be between 1 and 3 numeric digits (e.g. 123).", status_code=400)

    try:
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except Exception:
        raise AppError("Invalid date of birth format. Please use YYYY-MM-DD.", status_code=400)

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
        user.full_name = new_owner_name
        user.father_name = father_name
        user.mother_name = mother_name
        user.cnic_or_id_card = clean_cnic
        user.date_of_birth = dob
        user.edit_id_hash = hash_edit_id(normalize_edit_id(new_raw_edit_id))

    address.recipient_name = new_owner_name
    address.address_text = AddressFormatter.format_full(address)
    db.commit()
    db.refresh(address)

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
    session["user_id"] = user.id

    response = make_response(redirect(
        f"/address/{public_id}/view?owner_transferred=true&new_edit_id={new_raw_edit_id}",
        code=303
    ))
    response.set_cookie(
        key="edit_session_token",
        value=token_data["access_token"],
        httponly=True,
        max_age=settings.EDIT_SESSION_EXPIRE_MINUTES * 60,
        samesite="Lax"
    )
    return response
