from flask import Blueprint
from app.api.v1.auth import auth_api_bp
from app.api.v1.addresses import addresses_api_bp
from app.api.v1.resolve import resolve_api_bp
from app.api.v1.admin import admin_api_bp

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1_bp.register_blueprint(auth_api_bp)
api_v1_bp.register_blueprint(addresses_api_bp)
api_v1_bp.register_blueprint(resolve_api_bp)
api_v1_bp.register_blueprint(admin_api_bp)
