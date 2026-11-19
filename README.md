# CivicFix – Smart Public Complaint Management System

CivicFix is a Flask + SQLite college project for submitting, tracking and managing civic complaints. It includes an ML-based category suggestion prototype using TF-IDF and Logistic Regression.

## Features

### Citizen portal
- Citizen registration, login and logout (Werkzeug password hashing).
- Personal dashboard showing complaints submitted while signed in.
- Profile name/email editing.
- Complaint submission with optional image upload (JPG/JPEG/PNG/WEBP, maximum 5 MB; Pillow verifies actual image content).
- AI category suggestion endpoint and citizen-controlled category selection.
- Private tracking of account-linked complaints; only the owning account or admin can view account-linked complaint tracking.
- Status update timeline and in-app update feed on the citizen dashboard.
- Feedback/rating for resolved complaints.

### Admin portal
- Admin login and protected complaint management.
- Database-backed status statistics and category breakdown.
- Status changes and admin remarks, with status history.
- Search/filter in the complaint table.
- Registered citizen list (read-only).
- CSV and PDF exports.

### Security and reliability
- CSRF token validation on all POST requests.
- Parameterized SQLite queries and foreign-key enforcement.
- Hashed citizen passwords; admin password can be configured through environment variables or a Werkzeug password hash.
- HTTP-only and SameSite session cookies; HTTPS cookie mode can be enabled.
- UUID image filenames, extension allow-list, actual image decoding, and size limit.
- Database schema migrations run at startup to preserve older project databases.

## Requirements
- Windows 10/11, Python 3.10 or newer (Python 3.11 recommended)
- VS Code (recommended)
- Internet connection for the first dependency installation

## Installation (Windows PowerShell)
1. Extract this ZIP to a new folder. Keep your previous working project as a backup.
2. Open the extracted `CivicFix_Professional_Project` folder in VS Code (the folder containing `app.py`).
3. Open Terminal → New Terminal.
4. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use `venv\Scripts\activate.bat` from Command Prompt, or continue using `venv\Scripts\python.exe` explicitly.

5. Install packages:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

6. Configure a strong local admin password and secret key in the same terminal session:

```powershell
$env:CIVICFIX_ADMIN_USERNAME = "admin"
$env:CIVICFIX_ADMIN_PASSWORD = "Choose-A-Strong-Local-Password"
$env:CIVICFIX_SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
```

For a stronger admin-password setup, generate a Werkzeug hash using:

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Choose-A-Strong-Local-Password'))"
```

Then set `CIVICFIX_ADMIN_PASSWORD_HASH` to the printed value and remove `CIVICFIX_ADMIN_PASSWORD` from the environment. Do not commit secrets to GitHub. The built-in demo fallback is `admin` / `CivicFix@123`; change it before any demonstration on a shared network.

7. Run tests:

```powershell
python -m unittest discover -s tests -v
```

8. Start the local development server:

```powershell
python app.py
```

9. Open `http://127.0.0.1:5000` in your browser. Keep the terminal open while using the site. Press Ctrl+C to stop it.

## First-use demonstration
1. Open **Register** and create a citizen account using your own email and a password of at least 8 characters.
2. Sign in and open **Report Issue**. Submit a sample complaint, for example: “A large pothole is present on the main road and vehicles are having difficulty.”
3. Review the AI category suggestion. It is only a suggestion; the citizen can change the category.
4. Open **My Dashboard** and check the complaint appears.
5. Open a second browser/private session for admin testing. Visit `/admin/login` and use the configured admin credentials.
6. Update the complaint status and add an admin remark.
7. Return to the citizen session and refresh **My Dashboard** to see the status update. The user can submit a rating after the complaint is marked Resolved.
8. Admin can export CSV or PDF from the dashboard.

## Important routes
- `/` – public home page
- `/report` – submit a complaint
- `/track` – track a complaint (account-linked complaints are private)
- `/register`, `/login`, `/logout` – citizen account actions
- `/dashboard` – citizen dashboard (login required)
- `/profile` – edit profile (login required)
- `/admin/login`, `/admin`, `/admin/logout` – admin console
- `/admin/export.csv`, `/admin/export.pdf` – admin-only exports

## Database and files
- SQLite database: `civicfix.db` (created automatically in the project folder)
- Uploaded images: `uploads/`
- Schema reference: `schema.sql`
- Architecture and security notes: `docs/architecture.md`
- Technical scope and known limitations: `docs/TECHNICAL_REVIEW.md`

Back up `civicfix.db` and `uploads/` together. Do not delete the database if you need to preserve complaint records. Startup migrations add missing columns/tables to earlier CivicFix databases. Test migrations on a copy before using important data.

## AI model notes
`civic_ai.py` uses a small bundled demonstration dataset with TF-IDF and Logistic Regression. This demonstrates a real ML pipeline, but the training sample is small and is not a validated civic classifier. Evaluate on a separate labelled dataset, report precision/recall/F1, and expand the dataset before relying on predictions. Citizens must be able to override suggestions.

## Known limitations / not production-ready
- Admin authentication uses a single configured admin identity, not a multi-admin account system with role management.
- Email/SMS delivery is not configured; status notifications are displayed in the citizen dashboard based on status history.
- Citizen account-linked complaints are private by account ownership, but older anonymous complaints and newly submitted anonymous complaints still use the numeric public tracking workflow. Do not publish sensitive personal details in descriptions or locations.
- No live municipal integration, map/geocoding service, CAPTCHA, rate limiting, or duplicate detection is configured.
- The app uses Flask's local development server. For public deployment, use HTTPS and a production WSGI server, managed secrets, backups, rate limiting, monitoring, and a security/privacy review.
- Full browser/mobile visual QA depends on running the application on your own machine.

## GitHub safety
Before pushing to GitHub, exclude `venv/`, `__pycache__/`, `civicfix.db`, `uploads/*` (except `.gitkeep`), `.env`, and any secrets. Never upload real citizen data or photos.


## Final verification and remaining integrations
See `docs/REMAINING_IMPLEMENTATION_AND_VERIFICATION.md` for the full local acceptance checklist, monthly analytics and duplicate-warning details, and integrations that require external provider credentials (email/SMS, maps, CAPTCHA).
