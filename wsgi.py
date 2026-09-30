import os
import sys

# 1. Add project directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. Automatically ensure database tables & initial data exist
try:
    from app.database.session import init_db
    from app.seed import seed_database
    init_db()
    seed_database()
except Exception as e:
    print(f"WSGI startup notice: {e}")

# 3. Export Flask application as WSGI entry point
from app.main import app as application

if __name__ == "__main__":
    application.run()
