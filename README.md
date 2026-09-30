# Universal Address Resolution Platform

A production-ready physical address management and resolution web platform built with **Python 3.12+**, **FastAPI**, **SQLite (WAL mode)**, **SQLAlchemy 2.x**, **Pydantic v2**, and **Vanilla JavaScript**.

The platform enables users to create, store, manage, share, resolve, and navigate physical addresses through compact, stable 6-character **Public Address IDs** and smart URLs with zero external infrastructure requirements (no Docker, no Redis, no Celery, Windows-native).

---

## 🌟 Key Features

### 1. Smart Address Resolution & Driving Navigation
- **Public URL**: `http://127.0.0.1:8000/{public_id}` (e.g. `http://127.0.0.1:8000/ab1226`) with backward-compatible alias `http://127.0.0.1:8000/a/{public_id}`.
- **Auto-Copy to Clipboard**: Automatically attempts to copy the complete formatted physical address to the visitor's clipboard with instant visual feedback (`Address copied to clipboard`).
- **Manual Copy Fallback**: If browser clipboard permissions are blocked, displays a prominent, accessible "Copy Address" button.
- **Turn-by-Turn Driving Directions**:
  - Immediately reveals a **Google Maps Driving Navigation** button.
  - Formatted directly to Google Maps: `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving`.
  - Animates with a pulsing green glow upon copy completion.
- **Configurable Countdown & Redirect**: Waits for a user-specified delay (default: 3 seconds) before smoothly redirecting the visitor to the destination website or Google Maps navigation.

### 2. Interactive Map Pinning (Optional, Strongly Recommended ⭐)
- Built-in interactive map picker in Step 3 of address creation and editing.
- Users can click anywhere on the map or drag the pin to mark their exact doorstep or building entrance.
- **GPS Auto-Detect**: One-click "Detect My GPS Location" button queries device coordinates.
- Live coordinate synchronization (`latitude`, `longitude`) with test links to preview on Google Maps and test driving routes.

### 3. Passwordless Direct Address Creation (Edit ID)
- **Zero Passwords / No Login Required**: Anyone can add an address immediately.
- **Secret 13-Character Edit ID Formula**:
  $$\text{Edit ID} = [\text{Public ID}] + [\text{Father's Initial}] + [\text{Mother's Initial}] + [\text{CNIC Last 3}] + [\text{DOB YY}]$$
  *Example*: Public ID `ab1226`, Father `Muhammad` $\rightarrow$ `M`, Mother `Ayesha` $\rightarrow$ `A`, CNIC ending `123` $\rightarrow$ `123`, DOB `01-01-1991` $\rightarrow$ `91` gives:
  $$\mathbf{ab1226MA12391} \quad (6 + 1 + 1 + 3 + 2 = 13\text{ characters})$$
- **Strict 3-Digit CNIC Limit**: Input field strictly rejects non-digits and caps input at 3 digits (`inputmode="numeric"`, `maxlength="3"`).
- **A–Z Alphabet Dropdowns**: Clean selection for parents' initials without typing full names.
- **Delivery Phone Toggle**: Delivery courier contact number can be enabled or disabled with a single toggle.
- **Strictly Unique (Never Identical or Same)**: Edit IDs can never be identical across users. If two people share the exact same initials, ID ending, and DOB, the system automatically assigns an incremental suffix (e.g. `ab1226MA12391-2`), guaranteeing single-owner access.
- **Argon2id Hashed**: Edit IDs are salted and hashed with Argon2id; never exposed in public URLs or API responses.
- **Rate-Limiting & Lockout**: Brute-force protection with failed-attempt tracking and temporary lockout.

### 4. Dual Reach Scopes & Address Types
- **Two Delivery Reach Options**:
  - 🛵 **Local City Delivery (`LOCAL`)**: Optimized for intra-city couriers and food deliveries.
  - 🌍 **Out of City / Worldwide (`INTERNATIONAL`)**: Optimized for regional, domestic, and cross-border shipping.
- Supported Address Types: `DELIVERY`, `RESIDENTIAL`, `BUSINESS`, `POSTAL`, `LANDMARK`, `TEMPORARY`, `OTHER`.

### 5. Staged 6-Character Public ID Generation
- Exactly 6 characters, canonical lowercase, case-insensitive resolution (`AB1226` = `ab1226`).
- **Stage 1 (Default)**: `LLDDYY` ($26 \times 26 \times 10 \times 10 = 67,600$ IDs/year) where $YY$ is the permanent creation year.
- **Stage 2**: `LDDDYY` (activated only upon Stage 1 exhaustion).
- Collision-safe with database unique constraints and automatic retry.
- **Permanent Stability**: Editing an address archives an immutable snapshot (Version 2, 3...) while preserving the Public ID permanently.

### 6. Administration & Security
- Complete administrative dashboard (`/admin`) with user management, address controls, generator telemetry, access logs, and audit trails.
- Dedicated red **Admin Logout** button on headers and sidebars.
- Role-Based Access Control (`SUPER_ADMIN`, `ADMIN`, `MODERATOR`, `USER`).

---

## 🚀 Quick Start (Windows & Cross-Platform)

The project is managed exclusively through Python with zero external script dependencies.

### 1. Requirements
- Python 3.12+ installed and available on `PATH`.

### 2. Automatic Setup
Run the setup command to initialize virtual environment, install requirements, and seed the database:
```cmd
python run.py setup
```

### 3. Start the Web Server
Launch the application:
```cmd
python run.py
```
Or explicitly:
```cmd
python run.py start
```

Open your browser:
- **Web Application**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Public Address Resolver Demo**: [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo) (or [http://127.0.0.1:8000/a/demo](http://127.0.0.1:8000/a/demo))
- **Administrator Sign-In**: [http://127.0.0.1:8000/3210325048745](http://127.0.0.1:8000/3210325048745)

**Administrator Credentials**:
- Set credentials with: `python run.py set-admin <username> <password>`
- Or configure via `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `app/.env`

---

## 🧪 Running Automated Tests

Run the full pytest test suite (29 automated test cases covering public ID generation, stability, security, 3-digit CNIC limits, driving directions, and the 13-character Edit ID format):

```cmd
python run.py test
```

Pass custom pytest flags directly:
```cmd
python run.py test -v tests/test_addresses.py
python run.py test -k test_cnic
```

---

## ⚙️ CLI Management Commands

All operations are executed through `run.py`:

| Command | Action |
| :--- | :--- |
| `python run.py` | Starts the web server on `127.0.0.1:8000` (auto-detects virtualenv and DB) |
| `python run.py setup` | Automated environment setup (venv, pip requirements, database init, admin seed) |
| `python run.py test [ARGS]` | Runs the automated pytest test suite |
| `python run.py seed` | Re-seeds the database with default administrator and sample data |
| `python run.py migrate` | Runs database migrations using Alembic |
| `python run.py help` | Displays the help menu with all options |

---

## 📁 Repository Structure

The main project directory is kept clean and minimal:

```text
UniversalAddressResolutionPlatform/
├── README.md               # Complete platform documentation
├── requirements.txt        # Production and testing Python dependencies
├── run.py                  # All-in-one Python execution & management script
│
├── alembic/                # Database migrations & alembic.ini
│   ├── alembic.ini         # Alembic configuration
│   ├── env.py              # Migration environment
│   └── versions/           # Migration revisions
│
├── app/                    # Main application package
│   ├── api/                # FastAPI REST API v1 endpoints
│   ├── core/               # App configuration, security, exceptions, logging
│   ├── database/           # SQLAlchemy engine, session, Base metadata
│   ├── models/             # Database ORM models (User, Address, Version, etc.)
│   ├── repositories/       # Database access repositories
│   ├── schemas/            # Pydantic v2 validation models
│   ├── services/           # Core business logic (ID generator, resolver, auth)
│   ├── static/             # CSS & Vanilla JavaScript assets
│   ├── templates/          # Jinja2 HTML templates
│   ├── web/                # Web frontend routes (home, auth, address, resolver, admin)
│   └── seed.py             # Database seed script
│
├── data/                   # SQLite database directory (address_platform.db)
└── tests/                  # Pytest test suite (25 automated tests)
```

---

## 🔒 Security Architecture
- **No Sensitive Leakage**: The public resolver `/a/{public_id}` and `/api/v1/resolve/{public_id}` strictly never expose user IDs, passwords, Edit IDs, CNIC numbers, or dates of birth.
- **Argon2id Edit ID Security**: Edit IDs are normalized and cryptographically hashed before database storage.
- **Destination URL Sanitization**: Enforces strict URL safety checks (`http://` / `https://` only, rejects `javascript:`, data URIs, and dangerous schemes).
- **SQLite WAL Mode**: Configured with `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` for robust concurrent reads and writes without file locks.
