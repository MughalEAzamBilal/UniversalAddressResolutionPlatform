from flask import Blueprint, render_template, request, redirect, session, make_response
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.services.edit_id_service import EditIdService
from app.web.deps import get_current_web_user, get_client_ip
from app.core.exceptions import AppError
from app.core.config import get_settings
from app.models.user import UserRole

auth_bp = Blueprint("auth", __name__)
settings = get_settings()


@auth_bp.route("/3210325048745", methods=["GET"])
@auth_bp.route("/login", methods=["GET"])
def login_page():
    current_user = get_current_web_user()
    if current_user:
        return redirect("/dashboard", code=303)
    next_url = request.args.get("next", "")
    return render_template(
        "auth/login.html",
        next_url=next_url,
        current_user=None,
        active_nav="login"
    )


@auth_bp.route("/3210325048745", methods=["POST"])
@auth_bp.route("/login", methods=["POST"])
def login_submit():
    db = get_db()
    ip = get_client_ip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    next_url = request.form.get("next", "").strip()

    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate_password(username, password, ip_address=ip)
        token_data = auth_service.create_user_tokens(user)
        if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MODERATOR):
            default_dest = "/admin"
        else:
            default_dest = "/dashboard"
        redirect_url = next_url if next_url and next_url.startswith("/") else default_dest
        response = make_response(redirect(redirect_url, code=303))
        response.set_cookie(
            key="session_token",
            value=token_data["access_token"],
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="Lax"
        )
        return response
    except AppError as e:
        return render_template(
            "auth/login.html",
            error=e.message,
            next_url=next_url,
            current_user=None,
            active_nav="login"
        ), e.status_code


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    return redirect("/address/new", code=303)


@auth_bp.route("/edit", methods=["GET"])
def edit_id_portal_page():
    current_user = get_current_web_user()
    next_url = request.args.get("next", "")
    return render_template(
        "auth/edit_id_portal.html",
        next_url=next_url,
        current_user=current_user,
        active_nav="edit_id"
    )


@auth_bp.route("/edit", methods=["POST"])
def edit_id_portal_submit():
    db = get_db()
    ip = get_client_ip()
    edit_id = request.form.get("edit_id", "").strip()
    next_url = request.form.get("next", "").strip()

    try:
        user = EditIdService.verify_and_authenticate(db, edit_id, ip_address=ip)
        auth_service = AuthService(db)
        token_data = auth_service.create_edit_session_token(user)
        session["user_id"] = user.id

        redirect_url = next_url if (next_url and next_url.startswith("/")) else "/my-addresses"
        response = make_response(redirect(redirect_url, code=303))
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
            "auth/edit_id_portal.html",
            error=e.message,
            next_url=next_url,
            current_user=None,
            active_nav="edit_id"
        ), e.status_code


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    response = make_response(redirect("/", code=303))
    response.delete_cookie("session_token")
    response.delete_cookie("edit_session_token")
    return response
