from flask import Blueprint, request, jsonify
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.api.deps import get_client_ip, get_api_current_user
from app.core.security import rate_limiter
from app.core.exceptions import AppError
from app.schemas.auth import UserRegisterRequest

auth_api_bp = Blueprint("api_auth", __name__)


@auth_api_bp.route("/auth/register", methods=["POST"])
def register():
    ip = get_client_ip()
    if not rate_limiter.is_allowed(f"register_{ip}", max_requests=10, window_seconds=60):
        return jsonify({"detail": "Too many registration attempts. Please wait."}), 429

    data = request.get_json(silent=True) or {}
    db = get_db()
    auth_service = AuthService(db)
    try:
        req = UserRegisterRequest(**data)
        user, edit_id = auth_service.register(req)
        return jsonify({
            "message": "User registered successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
            },
            "edit_id": edit_id,
            "notice": "Please save your Edit ID securely. It allows you to access and edit your addresses."
        }), 201
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@auth_api_bp.route("/auth/login", methods=["POST"])
def login():
    ip = get_client_ip()
    if not rate_limiter.is_allowed(f"login_{ip}", max_requests=15, window_seconds=60):
        return jsonify({"detail": "Too many login attempts. Please wait."}), 429

    data = request.get_json(silent=True) or {}
    username_or_email = data.get("username_or_email", "")
    password = data.get("password", "")

    db = get_db()
    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate_password(username_or_email, password, ip_address=ip)
        token_data = auth_service.create_user_tokens(user)
        return jsonify(token_data)
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code


@auth_api_bp.route("/auth/edit-id-login", methods=["POST"])
def edit_id_login():
    data = request.get_json(silent=True) or {}
    edit_id = data.get("edit_id", "")
    ip = get_client_ip()
    db = get_db()
    try:
        user = EditIdService.verify_and_authenticate(db, edit_id, ip_address=ip)
        auth_service = AuthService(db)
        token_data = auth_service.create_edit_session_token(user)
        return jsonify(token_data)
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code


@auth_api_bp.route("/auth/me", methods=["GET"])
def me():
    try:
        user = get_api_current_user()
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        })
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code
