CIVICFIX — SMART PUBLIC COMPLAINT MANAGEMENT SYSTEM
===================================================

TECH STACK
- Frontend: HTML5, CSS3, JavaScript, Jinja2 templates
- Backend: Python 3.10+ and Flask
- Database: SQLite (civicfix.db)
- Upload validation: Pillow image decoder + extension allow-list
- Authentication: Flask signed session, server-side credential check

PROJECT STRUCTURE
CivicFix_Professional_Project/
  app.py                 Flask routes, validation, auth and database logic
  requirements.txt       Python dependencies
  schema.sql             Database schema reference
  civicfix.db            Created automatically on first run
  uploads/               Uploaded complaint photos
  templates/             Jinja2 HTML pages
  static/style.css       Responsive interface styling
  static/app.js          Small frontend enhancement
  tests/test_app.py      Automated integration smoke tests
  docs/architecture.md   Architecture and design notes

INSTALLATION (WINDOWS / VS CODE)
1. Extract the ZIP into a new folder.
2. Open that folder in VS Code (File > Open Folder).
3. Open Terminal > New Terminal.
4. Create and activate a virtual environment:
     python -m venv venv
     venv\Scripts\activate
5. Install dependencies:
     python -m pip install -r requirements.txt
6. Set a private admin password and secret key in PowerShell for this terminal:
     $env:CIVICFIX_ADMIN_USERNAME = "admin"
     $env:CIVICFIX_ADMIN_PASSWORD = "ChooseYourOwnStrongPassword"
     $env:CIVICFIX_SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
7. Start the application:
     python app.py
8. Open http://127.0.0.1:5000 in your browser.

LOCAL DEMO CREDENTIALS
If you do not set environment variables, the local demo defaults are:
  Username: admin
  Password: CivicFix@123
These are public demo defaults, not secure production credentials. Set your own
password and secret key before sharing the application or using real data.
Credentials are checked by the Flask backend and are not printed in page HTML.

PAGES / ROUTES
  /                  Public home page
  /report            Submit a complaint (GET/POST)
  /track             Track by numeric complaint ID
  /admin/login       Administrator sign-in
  /admin             Protected administrator dashboard
  /update_status/id  Protected status update (POST)
  /admin/logout      Protected logout (POST)
  /uploads/name      Serve an uploaded image

FEATURES
- Complaint registration with generated sequential tracking ID
- Server-side required-field and length validation
- Optional image upload, 5 MB limit, extension allow-list and actual image decoding
- Complaint tracking and current status
- Admin-only dashboard, complaint search/filter and status changes
- Flask session authentication and admin route protection
- CSRF token validation for POST forms
- SQLite schema migration for older reports tables
- UTC created/updated timestamps and complaint status history
- Responsive existing design retained
- Public tracker hides the citizen's submitted name

RUN TESTS
After installing requirements, from this project folder run:
  python -m unittest discover -s tests -v
The tests cover home, protected admin access, valid complaint submission with a
real image, tracking, admin login, status updates, status history, logout, CSRF
rejection and invalid image rejection.

DATABASE / BACKUP
- civicfix.db is created automatically beside app.py.
- Existing civicfix.db data is preserved; missing status/timestamp columns are
  added automatically. Back up the database before replacing project files.
- Copy civicfix.db and uploads/ to back up submitted complaints and photos.

IMPORTANT LIMITATIONS
- This is a college mini-project/local demonstration, not a production civic
  service. Use HTTPS, a production WSGI server, a secret manager, stronger
  administrator account management, rate limiting, audit monitoring and
  privacy/legal review before public deployment.
- Tracking IDs are sequential and therefore guessable. For a real public
  deployment, add a separate unguessable tracking token or citizen account.
- No user registration/dashboard, email/SMS notifications, live maps or AI
  classifier is claimed as implemented. These are future enhancements.
- Debug mode is OFF by default. For local debugging only, set:
    $env:CIVICFIX_DEBUG = "1"
  Never expose the Flask development server or debugger to the internet.
- Google Fonts need an internet connection; system fonts are used as fallback.


AI CATEGORY SUGGESTION (EDUCATIONAL PROTOTYPE)
- The report form uses TF-IDF text features and a Logistic Regression classifier.
- It suggests one of the existing complaint categories from the description.
- The citizen must review the suggestion and can change the category.
- The built-in training examples are a small demonstration dataset, not real municipal data.
- Predictions may be wrong. Do not treat the displayed confidence as a guarantee.
- For a stronger academic model, collect reviewed and consented local examples, split them into train/test sets, measure precision/recall/F1, and retrain with representative data.
- The classifier is trained locally when first needed; no external AI API is called.

LATEST REVIEW UPDATE
--------------------
The reviewed build includes admin remarks, a Rejected complaint status, and a protected CSV export at /admin/export.csv (available only after admin login). The SQLite migration adds the admin_remarks column automatically to an existing database.

IMPORTANT FEATURE LIMITATIONS
-----------------------------
This version does not yet include citizen registration/login, a personal user dashboard, profile editing, notifications, citizen feedback, or PDF reports. Do not describe these as implemented in a project demonstration. The AI model is an educational prototype trained on a small built-in example set; it suggests categories but does not guarantee correct predictions.

Run tests after installing requirements:
    python -m unittest discover -s tests -v

Security reminder: configure CIVICFIX_ADMIN_USERNAME, CIVICFIX_ADMIN_PASSWORD and CIVICFIX_SECRET_KEY for your local demo. Do not publish the demo password, secrets, uploaded personal data or civicfix.db.
