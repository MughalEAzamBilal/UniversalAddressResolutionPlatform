"""
Universal Address Resolution Platform
All-in-one Management & Execution Script (Python 3.12+)

Commands:
  python run.py               -> Start the Flask web server (Default)
  python run.py start         -> Start the Flask web server
  python run.py setup         -> Setup virtual environment, install requirements, init & seed DB
  python run.py test          -> Run pytest test suite
  python run.py seed          -> Seed database with initial admin and sample addresses
  python run.py --help        -> Display help & available commands
"""

import os
import sys
import subprocess
import shutil

# Project Root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# Virtual Environment Python Detection
if sys.platform == "win32":
    VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")

# Auto-detect and switch to virtual environment immediately for all commands except setup
is_setup_cmd = len(sys.argv) > 1 and sys.argv[1].lower() in ("setup", "install", "--setup")
if not is_setup_cmd and os.path.exists(VENV_PYTHON):
    current_py = os.path.abspath(sys.executable).lower()
    target_py = os.path.abspath(VENV_PYTHON).lower()
    if current_py != target_py:
        cmd = [VENV_PYTHON, os.path.abspath(__file__)] + sys.argv[1:]
        try:
            sys.exit(subprocess.call(cmd))
        except KeyboardInterrupt:
            sys.exit(0)


def run_setup():
    """Initializes virtual environment, installs dependencies, and sets up database."""
    print("=" * 64)
    print("Universal Address Resolution Platform — Automated Setup")
    print("=" * 64)

    # 1. Virtual Environment
    venv_dir = os.path.join(PROJECT_ROOT, ".venv")
    if not os.path.exists(venv_dir):
        print("\n[1/4] Creating Python virtual environment in .venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"])
        print("✓ Virtual environment created.")
    else:
        print("\n[1/4] Virtual environment (.venv) already exists.")

    py_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

    # 2. Dependencies
    req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_file):
        print("\n[2/4] Installing / updating dependencies from requirements.txt ...")
        subprocess.check_call([py_exe, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([py_exe, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully.")

    # 3. Environment configuration
    env_file = os.path.join(PROJECT_ROOT, "app", ".env")
    env_example = os.path.join(PROJECT_ROOT, "app", ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        print("\n[3/4] Initializing app/.env from template ...")
        shutil.copyfile(env_example, env_file)
        print("✓ Configuration initialized.")
    else:
        print("\n[3/4] Configuration verified.")

    # 4. Database initialization & seed
    print("\n[4/4] Initializing database & seeding administrator ...")
    subprocess.check_call([py_exe, "-c", "from app.seed import seed_database; seed_database()"])
    print("✓ Database setup & seeding complete.")

    print("\n" + "=" * 64)
    print("Setup finished! Start the application by running: python run.py")
    print("=" * 64)


def run_tests(extra_args):
    """Executes pytest suite."""
    py_exe = sys.executable
    cmd = [py_exe, "-m", "pytest", "-o", "asyncio_mode=auto", "-W", "ignore::DeprecationWarning"]
    if not extra_args:
        cmd.extend(["-v", "tests"])
    else:
        cmd.extend(extra_args)

    print("Running Universal Address Platform Test Suite...")
    sys.exit(subprocess.call(cmd))


def run_seed():
    """Seeds the database."""
    from app.seed import seed_database
    seed_database()


def run_migrate():
    """Runs Alembic migrations programmatically."""
    ini_path = os.path.join(PROJECT_ROOT, "alembic", "alembic.ini")
    if not os.path.exists(ini_path):
        print(f"Error: {ini_path} not found.")
        sys.exit(1)
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(ini_path)
        command.upgrade(alembic_cfg, "head")
        print("✓ Alembic migrations applied successfully.")
    except Exception as e:
        print(f"Migration error: {e}")
        sys.exit(1)


def run_server():
    """Starts the Flask web server."""
    # Ensure DB & Seed on first start
    try:
        from app.database.session import init_db
        from app.seed import seed_database
        init_db()
        seed_database()
    except Exception as e:
        print(f"Notice during startup check: {e}")

    from app.main import app
    from app.core.config import get_settings
    settings = get_settings()

    print("\n" + "=" * 64)
    print(f"  {settings.APP_NAME} (Flask Edition)")
    print("=" * 64)
    print(f"  * Web Application URL:   {settings.PUBLIC_BASE_URL}")
    print(f"  * Create Address:        {settings.PUBLIC_BASE_URL}/address/new")
    print(f"  * Admin Panel:           {settings.PUBLIC_BASE_URL}/admin")
    print(f"  * Default Admin Login:   admin / Admin123456!")
    print("=" * 64 + "\n")

    try:
        app.run(
            host="127.0.0.1",
            port=8000,
            debug=settings.DEBUG
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)


def print_help():
    print("""Universal Address Resolution Platform CLI

Usage:
  python run.py [COMMAND] [OPTIONS]

Commands:
  start               Start the web server (Default when no command provided)
  setup               Create virtual environment, install requirements & setup DB
  test [ARGS]         Run pytest suite (e.g. python run.py test -k test_edit_id)
  seed                Seed database with initial admin and sample addresses
  migrate             Execute Alembic migrations to upgrade database schema
  help, --help, -h    Show this help message

Examples:
  python run.py
  python run.py setup
  python run.py test
  python run.py test -v tests/test_addresses.py
""")


if __name__ == "__main__":
    args = sys.argv[1:]
    command = args[0].lower() if args else "start"

    if command in ("start", "serve", "server"):
        run_server()
    elif command in ("setup", "install", "--setup"):
        run_setup()
    elif command in ("test", "tests", "--test"):
        run_tests(args[1:])
    elif command in ("seed", "--seed"):
        run_seed()
    elif command in ("migrate", "migration", "--migrate"):
        run_migrate()
    elif command in ("help", "--help", "-h"):
        print_help()
    else:
        # If user passed uvicorn/pytest options directly or unknown
        print(f"Unknown command: '{command}'\n")
        print_help()
        sys.exit(1)
