from flask import Blueprint, request, jsonify
from app.database.session import get_db
from app.schemas.resolver import ResolutionResponse
from app.services.resolver_service import ResolverService
from app.api.deps import get_client_ip
from app.core.security import rate_limiter
from app.core.exceptions import AppError

resolve_api_bp = Blueprint("api_resolve", __name__)


@resolve_api_bp.route("/resolve/<public_id>", methods=["GET"])
def resolve_address_get(public_id: str):
    ip = get_client_ip()
    if not rate_limiter.is_allowed(f"resolve_{ip}", max_requests=60, window_seconds=60):
        return jsonify({"detail": "Too many resolution requests."}), 429

    db = get_db()
    service = ResolverService(db)
    try:
        user_agent = request.headers.get("User-Agent")
        referrer = request.headers.get("Referer")
        resolved = service.resolve(
            public_id=public_id,
            ip_address=ip,
            user_agent=user_agent,
            referrer=referrer
        )
        if hasattr(resolved, "model_dump"):
            return jsonify(resolved.model_dump())
        elif hasattr(resolved, "dict"):
            return jsonify(resolved.dict())
        return jsonify(resolved)
    except AppError as e:
        return jsonify({"detail": e.message}), e.status_code


@resolve_api_bp.route("/resolve", methods=["POST"])
def resolve_address_post():
    data = request.get_json(silent=True) or {}
    public_id = data.get("public_id", "")
    return resolve_address_get(public_id)
