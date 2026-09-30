import os
from flask import Flask, render_template, request, jsonify, Response
from app.core.config import get_settings
from app.core.logging import setup_logging, logger
from app.database.session import init_db, close_db
from app.web.deps import get_current_web_user

# Web & API Blueprints
from app.web.home import home_bp
from app.web.auth import auth_bp
from app.web.dashboard import dashboard_bp
from app.web.addresses import addresses_bp
from app.web.admin import admin_bp
from app.web.resolver import resolver_bp
from app.api.v1 import api_v1_bp

settings = get_settings()


def create_app() -> Flask:
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} (Flask)...")
    init_db()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static"
    )
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    # Register blueprints (order matters: specific routes first, resolver wildcard last)
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(addresses_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(resolver_bp)

    # Teardown database session at end of each request
    app.teardown_appcontext(close_db)

    # Global context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            "app_name": settings.APP_NAME,
            "base_url": settings.PUBLIC_BASE_URL,
            "current_user": get_current_web_user()
        }

    # Favicon route
    @app.route("/favicon.ico")
    def favicon():
        return Response("", status=204)

    # Global error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"detail": "Resource not found."}), 404
        return render_template(
            "resolver/error.html",
            status_code=404,
            error_title="Page Not Found",
            error_message="The requested page or address does not exist.",
            public_id=""
        ), 404

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"detail": "Forbidden."}), 403
        return render_template(
            "resolver/error.html",
            status_code=403,
            error_title="Access Forbidden",
            error_message="You do not have permission to view this resource.",
            public_id=""
        ), 403

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        if request.path.startswith("/api/"):
            return jsonify({"detail": "Internal server error."}), 500
        return render_template(
            "resolver/error.html",
            status_code=500,
            error_title="Server Error",
            error_message="An unexpected server error occurred.",
            public_id=""
        ), 500

    return app


app = create_app()
# Direct WSGI application callable for PythonAnywhere, Gunicorn, Waitress
application = app
