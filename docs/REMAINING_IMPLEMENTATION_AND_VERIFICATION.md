# CivicFix – Remaining Implementation and Verification Guide

## Added in this package

1. **Monthly complaint analytics:** Admin dashboard now displays database-backed complaint totals for the latest six calendar months.
2. **Possible duplicate warning:** Before saving a report, the app checks for a complaint with the same category and location in the previous 24 hours. It warns but does not block legitimate repeat reports; the citizen must confirm to continue.
3. **Automated tests:** Added test cases for duplicate-warning confirmation and monthly analytics rendering.

## Still external / production-oriented (not silently claimed as implemented)

- Email/SMS requires a provider account, credentials, consent, and delivery configuration.
- Maps/geocoding requires a map provider and API key.
- CAPTCHA requires a provider and site/secret keys.
- Multi-admin roles need a defined role/permission policy.
- Production rate limiting should use a shared backend (for example Redis) and reverse-proxy controls; a process-local counter is not sufficient across multiple workers.
- AI quality requires a larger, reviewed, representative dataset and a held-out test set. Do not report accuracy based only on training examples.
- Real municipal deployment requires privacy, retention, accessibility, security, and operational review.

## Local setup

Use Python 3.10 or newer. In the project directory:

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
$env:CIVICFIX_ADMIN_USERNAME = "admin"
$env:CIVICFIX_ADMIN_PASSWORD = "SetYourOwnStrongPassword"
$env:CIVICFIX_SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
python -m unittest discover -s tests -v
python app.py
```

Open `http://127.0.0.1:5000`. Keep the terminal open while using the app. Stop it with Ctrl+C.

## Manual acceptance checklist

- [ ] Register a citizen account; attempt duplicate email registration.
- [ ] Log in and log out; confirm dashboard requires login.
- [ ] Submit a complaint with and without an image.
- [ ] Upload a renamed non-image file and an oversized file; confirm safe rejection.
- [ ] Submit a same-category/same-location complaint within 24 hours; confirm warning appears and the citizen can either stop or confirm.
- [ ] Confirm a citizen sees only their account-linked complaints and status notices.
- [ ] Log in as admin; update status and remarks; confirm status history changes.
- [ ] Check monthly dashboard counts against the actual records and dates in SQLite.
- [ ] Download CSV and PDF reports and open them.
- [ ] Submit feedback only for a resolved complaint; confirm a second citizen cannot rate it.
- [ ] Check all pages at desktop and mobile widths.
- [ ] Back up `civicfix.db` and `uploads/` before any migration or reset.

## Verification honesty

The package's Python syntax can be checked with `python -m py_compile app.py tests/test_app.py`. Runtime tests must be run on the user's machine after dependencies install. A successful static compile is not proof that the full browser workflow works. Record the actual test output in your project report; do not mark unchecked items as passed.
