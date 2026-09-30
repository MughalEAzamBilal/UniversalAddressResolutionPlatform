from flask import Blueprint, request, jsonify
from app.database.session import get_db
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse
from app.services.address_service import AddressService
from app.api.deps import get_api_current_user
from app.models.user import UserRole
from app.core.exceptions import AppError

addresses_api_bp = Blueprint("api_addresses", __name__)


@addresses_api_bp.route("/addresses", methods=["POST"])
def create_address():
    current_user = get_api_current_user()
    data = request.get_json(silent=True) or {}
    db = get_db()
    service = AddressService(db)
    try:
        addr_create = AddressCreate(**data)
        address = service.create_address(user_id=current_user.id, data=addr_create)
        resp = AddressResponse.model_validate(address).model_dump()
        return jsonify(resp), 201
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@addresses_api_bp.route("/addresses", methods=["GET"])
def list_addresses():
    current_user = get_api_current_user()
    db = get_db()
    service = AddressService(db)
    search = request.args.get("search")
    address_type = request.args.get("address_type")
    location_scope = request.args.get("location_scope")
    is_active = request.args.get("is_active")
    active_bool = None
    if is_active == "true":
        active_bool = True
    elif is_active == "false":
        active_bool = False

    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 50))

    addresses = service.list_user_addresses(
        user_id=current_user.id,
        search=search,
        address_type=address_type,
        location_scope=location_scope,
        is_active=active_bool,
        skip=skip,
        limit=limit
    )
    resps = [AddressResponse.model_validate(a).model_dump() for a in addresses]
    return jsonify(resps)


@addresses_api_bp.route("/addresses/<public_id>", methods=["GET"])
def get_address(public_id: str):
    current_user = get_api_current_user()
    db = get_db()
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    address = service.get_by_public_id(public_id, user_id=current_user.id, is_admin=is_admin)
    return jsonify(AddressResponse.model_validate(address).model_dump())


@addresses_api_bp.route("/addresses/<public_id>", methods=["PUT"])
def update_address(public_id: str):
    current_user = get_api_current_user()
    data = request.get_json(silent=True) or {}
    db = get_db()
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    try:
        update_data = AddressUpdate(**data)
        updated = service.update_address(
            public_id=public_id,
            user_id=current_user.id,
            data=update_data,
            is_admin=is_admin
        )
        return jsonify(AddressResponse.model_validate(updated).model_dump())
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@addresses_api_bp.route("/addresses/<public_id>/deactivate", methods=["POST"])
def deactivate_address(public_id: str):
    current_user = get_api_current_user()
    db = get_db()
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    service.set_active_status(public_id, user_id=current_user.id, is_active=False, is_admin=is_admin)
    return jsonify({"public_id": public_id, "is_active": False})


@addresses_api_bp.route("/addresses/<public_id>/activate", methods=["POST"])
def activate_address(public_id: str):
    current_user = get_api_current_user()
    db = get_db()
    service = AddressService(db)
    is_admin = current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)
    service.set_active_status(public_id, user_id=current_user.id, is_active=True, is_admin=is_admin)
    return jsonify({"public_id": public_id, "is_active": True})
