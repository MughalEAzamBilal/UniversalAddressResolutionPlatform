# Complete Step-by-Step Guide: Deploying to PythonAnywhere (pythonanywhere.com)

This guide walks you through deploying the **Universal Address Resolution Platform** to [PythonAnywhere](https://www.pythonanywhere.com) from scratch.

---

## Architecture Note: FastAPI on PythonAnywhere
PythonAnywhere uses **WSGI** web servers. FastAPI is an asynchronous **ASGI** framework.
To make FastAPI run with maximum performance on PythonAnywhere, this project includes **`a2wsgi`** and a pre-configured entrypoint [`wsgi.py`](file:///c:/Users/Mughal%20e%20Azam%20Bilal/Downloads/WebProjects/UniversalAddressResolutionPlatform/wsgi.py).

---

## Prerequisites
1. An account on [PythonAnywhere.com](https://www.pythonanywhere.com) (Free "Beginner" tier or any paid tier).
2. Your PythonAnywhere username (referred to as `YOUR_USERNAME` below).

---

## Step 1: Open a Bash Console on PythonAnywhere
1. Log in to your [PythonAnywhere Dashboard](https://www.pythonanywhere.com/user/).
2. In the top navigation, click on **Consoles**.
3. Under **Start a new console**, click on **Bash**.

---

## Step 2: Upload or Clone the Project
You have two choices to get your project files onto PythonAnywhere:

### Option A: Using Git (Recommended)
If you pushed your repository to GitHub / GitLab, run:
```bash
git clone <YOUR_GIT_REPOSITORY_URL> UniversalAddressResolutionPlatform
cd UniversalAddressResolutionPlatform
```

### Option B: Using ZIP Upload
1. On your local computer, zip the `UniversalAddressResolutionPlatform` folder (excluding `.venv` and `data/address_platform.db`).
2. In PythonAnywhere, go to the **Files** tab.
3. Upload `UniversalAddressResolutionPlatform.zip` to your home directory (`/home/YOUR_USERNAME/`).
4. In the Bash Console, extract it:
```bash
unzip UniversalAddressResolutionPlatform.zip -d UniversalAddressResolutionPlatform
cd UniversalAddressResolutionPlatform
```

---

## Step 3: Create a Virtual Environment & Install Dependencies
Inside your Bash Console, run:

```bash
# Ensure you are in the project folder
cd ~/UniversalAddressResolutionPlatform

# Create a virtual environment using Python 3.10 (or 3.11/3.12 if available on your account)
python3.10 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install all required packages
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4: Configure Production Environment Variables
Create the production environment configuration file:

```bash
cp app/.env.example app/.env
nano app/.env
```

Set the values as follows (replace `YOUR_USERNAME` with your actual PythonAnywhere username):

```ini
APP_NAME=Universal Address Resolution Platform
APP_ENV=production
DEBUG=False
SECRET_KEY=ReplaceWithAStrongRandomSecretStringAtLeast32CharsLong!
DATABASE_URL=sqlite:////home/YOUR_USERNAME/UniversalAddressResolutionPlatform/data/address_platform.db
PUBLIC_BASE_URL=https://YOUR_USERNAME.pythonanywhere.com
DEFAULT_REDIRECT_SECONDS=3
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EDIT_SESSION_EXPIRE_MINUTES=60
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15
```

> **Note**: Press `Ctrl + O` then `Enter` to save in nano, then `Ctrl + X` to exit.

---

## Step 5: Initialize the Database & Seed Admin
In the activated Bash console, run:

```bash
python run.py seed
```

This creates the SQLite database in `data/address_platform.db` and seeds the administrator account:
- **Default Admin Login**: `admin`
- **Default Admin Password**: `Admin123456!`
*(Log in through `/3210325048745` and change the password immediately in production).*

---

## Step 6: Create & Configure the Web App in PythonAnywhere

1. Click on the **Web** tab at the top of the PythonAnywhere dashboard.
2. Click **Add a new web app**.
3. When prompted about your domain name:
   - If using a free account, choose the default `YOUR_USERNAME.pythonanywhere.com`.
   - If using a paid custom domain, enter your domain name.
4. On the framework selection page:
   - Choose **Manual configuration** *(Do NOT select Flask or Django)*.
   - Choose **Python 3.10** (matching the Python version used for your `.venv`).
   - Click **Next** to finish the wizard.

### Configure Web App Settings

#### 1. Code Section:
- **Source code**: `/home/YOUR_USERNAME/UniversalAddressResolutionPlatform`
- **Working directory**: `/home/YOUR_USERNAME/UniversalAddressResolutionPlatform`

#### 2. Virtualenv Section:
- Click on **Enter path to a virtualenv, if you would like to use one**:
- Enter: `/home/YOUR_USERNAME/UniversalAddressResolutionPlatform/.venv`
- Click the checkmark to save.

#### 3. WSGI Configuration File:
- In the **Code** section, click on the WSGI configuration file link (e.g. `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`).
- Delete all default contents and replace them with:

```python
import os
import sys

# 1. Project path
project_home = '/home/YOUR_USERNAME/UniversalAddressResolutionPlatform'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2. Import WSGI application using a2wsgi adapter
from wsgi import application
```
*(Replace `YOUR_USERNAME` with your actual username)*.
- Click the green **Save** button in the top right.

#### 4. Static Files Section:
Under the **Static files** table, add this mapping:
- **URL**: `/static/`
- **Directory**: `/home/YOUR_USERNAME/UniversalAddressResolutionPlatform/app/static`

#### 5. Security:
- Scroll down to the **Security** section.
- Turn ON **Force HTTPS**.

---

## Step 7: Reload & Launch!

1. Scroll to the top of the **Web** tab.
2. Click the big green button: **Reload YOUR_USERNAME.pythonanywhere.com**.
3. Open your browser and navigate to:
   - `https://YOUR_USERNAME.pythonanywhere.com`
   - Test address creation at: `https://YOUR_USERNAME.pythonanywhere.com/address/new`
   - Test address resolving at: `https://YOUR_USERNAME.pythonanywhere.com/demo`
   - Access the hidden admin login at: `https://YOUR_USERNAME.pythonanywhere.com/3210325048745`

---

## Troubleshooting & Maintenance

- **View Logs**:
  If you see "Something went wrong" or a 500 error, check the logs on the **Web** tab:
  - **Error log**: `/var/log/YOUR_USERNAME.pythonanywhere.com.error.log`
  - **Server log**: `/var/log/YOUR_USERNAME.pythonanywhere.com.server.log`
- **Updating Code**:
  Whenever you pull new code or change files:
  ```bash
  cd ~/UniversalAddressResolutionPlatform
  git pull
  ```
  Then click **Reload** on the PythonAnywhere **Web** tab.
- **SQLite Database Backup**:
  Download or copy `/home/YOUR_USERNAME/UniversalAddressResolutionPlatform/data/address_platform.db` anytime for a complete backup.
