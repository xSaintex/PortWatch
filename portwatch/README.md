# PortWatch

PortWatch is a Flask web application for scanning authorized school laboratory
devices for open ports using Nmap and comparing results against a per-device allowlist.

---

## Quick Setup on Windows

Follow these steps to get the app running on your Windows machine.

### 1. Open a Terminal in the Project Folder

Open PowerShell or Command Prompt, then navigate to the `portwatch` folder:

```
cd path\to\portwatch
```

### 2. Create a Virtual Environment

A virtual environment keeps the project's Python packages separate from the rest
of your system. Run this command once:

```
python -m venv venv
```

This creates a new folder called `venv` inside the project.

### 3. Activate the Virtual Environment

Every time you open a new terminal to work on this project, run:

```
venv\Scripts\activate
```

You will see `(venv)` at the start of your terminal prompt. That means it worked.

### 4. Install the Required Packages

```
pip install -r requirements.txt
```

### 5. Run the Application

```
python run.py
```

### 6. Open in Your Browser

Go to: **http://127.0.0.1:5000**

You should see the PortWatch Admin Dashboard.

---

## What Each Main Folder Does

| Folder / File | Purpose |
|---|---|
| `run.py` | Starts the Flask development server. Always run this file. |
| `config.py` | App-wide settings: secret key, debug mode. |
| `requirements.txt` | List of Python packages the app needs. |
| `app/` | The main application package. |
| `app/__init__.py` | The app factory — creates and configures the Flask app. |
| `app/routes/` | URL route definitions. Each file handles a section of the app. |
| `app/mock_data/` | Sample data used while the real database is not yet built. |
| `app/templates/` | HTML templates rendered by Flask (Jinja2). |
| `app/templates/base/` | The shared page skeleton all pages extend. |
| `app/templates/partials/` | Reusable pieces of HTML (navbar, sidebar, banners). |
| `app/templates/admin/` | Pages only the Administrator role can see. |
| `app/templates/viewer/` | Pages for the Viewer role (not built yet). |
| `app/static/css/` | Stylesheets. `portwatch_theme.css` is the main theme file. |
| `app/static/js/` | JavaScript files for charts and interactive behaviour. |
| `app/static/img/` | Images and logos. |

---

## Stopping the Server

Press `Ctrl + C` in the terminal to stop Flask.

## Deactivating the Virtual Environment

When you are done working, run:

```
deactivate
```

---

## Demo Accounts (for testing only)

| Username | Password | Full Name | Role |
|---|---|---|---|
| admin | `Admin123!` | System Administrator | Administrator |
| viewer | `Viewer123!` | Demo Viewer | Viewer |
| kdeleon | `PortWatch123` | Karl De Leon | Administrator |
| jdelacruz | `PortWatch123` | Jose Dela Cruz | Viewer |

⚠️ **Never use these credentials in a real deployment.**

## Login

Open **http://127.0.0.1:5000** — you will be redirected to the login page.
Enter one of the demo accounts above to sign in.
