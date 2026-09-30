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
        print("[OK] Virtual environment created.")
    else:
        print("\n[1/4] Virtual environment (.venv) already exists.")

    py_exe = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

    # 2. Dependencies
    req_file = os.path.join(PROJECT_ROOT, "requirements.txt")
    if os.path.exists(req_file):
        print("\n[2/4] Installing / updating dependencies from requirements.txt ...")
        subprocess.check_call([py_exe, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([py_exe, "-m", "pip", "install", "-r", "requirements.txt"])
        print("[OK] Dependencies installed successfully.")

    # 3. Environment configuration
    env_file = os.path.join(PROJECT_ROOT, "app", ".env")
    env_example = os.path.join(PROJECT_ROOT, "app", ".env.example")
    if not os.path.exists(env_file) and os.path.exists(env_example):
        print("\n[3/4] Initializing app/.env from template ...")
        shutil.copyfile(env_example, env_file)
        print("[OK] Configuration initialized.")
    else:
        print("\n[3/4] Configuration verified.")

    # 4. Database initialization & seed
    print("\n[4/4] Initializing database & seeding administrator ...")
    subprocess.check_call([py_exe, "-c", "from app.seed import seed_database; seed_database()"])
    print("[OK] Database setup & seeding complete.")

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


def set_admin_credentials(args):
    """Sets or updates the administrator username and password."""
    username = args[0] if len(args) > 0 else None
    password = args[1] if len(args) > 1 else None

    if not username:
        username = input("Enter new admin username: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("Enter new admin password: ").strip()

    if not username or not password:
        print("Error: Both username and password are required.")
        sys.exit(1)

    from app.database.session import SessionLocal, init_db
    from app.models.user import User, UserRole, AccountStatus
    from app.core.security import hash_password
    init_db()
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN])).first()
        if admin:
            admin.username = username
            admin.password_hash = hash_password(password)
            admin.account_status = AccountStatus.ACTIVE
            admin.failed_login_attempts = 0
            admin.locked_until = None
            db.commit()
            print(f"[OK] Administrator credentials updated & unlocked for user '{username}'.")
        else:
            from datetime import date, datetime, timezone
            from app.services.edit_id_service import EditIdService
            from app.core.security import hash_edit_id
            dob = date(1985, 1, 1)
            raw_edit_id = EditIdService.generate_edit_id("ab1226", "Muhammad", "Amina", "786", dob)
            admin = User(
                username=username,
                email=f"{username}@universaladdress.local",
                public_id="ab1226",
                full_name="Platform Administrator",
                father_name="Muhammad",
                mother_name="Amina",
                cnic_or_id_card="786",
                date_of_birth=dob,
                password_hash=hash_password(password),
                edit_id_hash=hash_edit_id(raw_edit_id),
                role=UserRole.SUPER_ADMIN,
                account_status=AccountStatus.ACTIVE,
                created_at=datetime.now(timezone.utc)
            )
            db.add(admin)
            db.commit()
            print(f"[OK] Administrator '{username}' created successfully.")
    finally:
        db.close()


def restore_backup(args):
    """Restores database from a specified SQLite backup file or the latest backup in data/backups/."""
    from app.core.config import get_settings
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite"):
        print("Error: Restore is only supported for SQLite databases.")
        sys.exit(1)

    target_db_path = os.path.abspath(db_url.replace("sqlite:///", ""))
    backups_dir = os.path.join(os.path.dirname(target_db_path), "backups")

    backup_file = args[0] if len(args) > 0 else None
    if not backup_file:
        if os.path.exists(backups_dir):
            available = sorted([f for f in os.listdir(backups_dir) if f.endswith(".db")])
            if available:
                backup_file = os.path.join(backups_dir, available[-1])
                print(f"No backup path specified. Using latest detected backup: {available[-1]}")
            else:
                print("Error: No backup specified and none found in data/backups/.")
                sys.exit(1)
        else:
            print("Error: Please provide path to backup: python run.py restore <backup.db>")
            sys.exit(1)

    if not os.path.exists(backup_file):
        print(f"Error: Backup file not found: {backup_file}")
        sys.exit(1)

    import sqlite3
    import shutil
    try:
        test_conn = sqlite3.connect(backup_file)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = test_cursor.fetchall()
        test_conn.close()
        if not tables:
            print("Error: Backup file contains no tables.")
            sys.exit(1)
    except Exception as e:
        print(f"Error: Corrupted database file: {e}")
        sys.exit(1)

    for suffix in ("-wal", "-shm", "-journal"):
        lock_file = target_db_path + suffix
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass

    os.makedirs(os.path.dirname(target_db_path), exist_ok=True)
    shutil.copyfile(backup_file, target_db_path)
    print(f"[OK] Database successfully restored from '{backup_file}'.")
    print(f"[OK] Active database is now: {target_db_path}")


def print_help():
    print("""Universal Address Resolution Platform CLI

Usage:
  python run.py [COMMAND] [OPTIONS]

Commands:
  start                     Start the web server (Default when no command provided)
  setup                     Create virtual environment, install requirements & setup DB
  test [ARGS]               Run pytest suite (e.g. python run.py test -k test_edit_id)
  seed                      Seed database with initial admin and sample addresses
  set-admin [USER] [PASS]   Change administrator username and password
  restore [FILE]            Restore database from a .db backup file
  help, --help, -h          Show this help message

Examples:
  python run.py
  python run.py setup
  python run.py set-admin admin MySecretPass123!
  python run.py restore data/backups/backup_20260930_121951.db
  python run.py test
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
    elif command in ("set-admin", "change-admin", "admin-credentials"):
        set_admin_credentials(args[1:])
    elif command in ("restore", "restore-backup", "backup-restore"):
        restore_backup(args[1:])
    elif command in ("help", "--help", "-h"):
        print_help()
    else:
        # If user passed options directly or unknown
        print(f"Unknown command: '{command}'\n")
        print_help()
        sys.exit(1)
