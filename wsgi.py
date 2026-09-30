"""
WSGI Application Entrypoint for PythonAnywhere & Production WSGI Servers
Converts the FastAPI ASGI application into a WSGI application using a2wsgi.
"""
import os
import sys

# Ensure current project directory is at the top of sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables from app/.env if present
from dotenv import load_dotenv
env_path = os.path.join(PROJECT_ROOT, "app", ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# Initialize database & seed admin if needed
try:
    from app.database.session import init_db
    from app.seed import seed_database
    init_db()
    seed_database()
except Exception as exc:
    print(f"[WSGI Init Warning]: {exc}", file=sys.stderr)

# Import the FastAPI application
from app.main import app
from a2wsgi import ASGIMiddleware

# PythonAnywhere looks for the WSGI callable named `application`
application = ASGIMiddleware(app)
