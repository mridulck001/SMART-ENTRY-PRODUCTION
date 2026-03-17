# NIELIT Smart Entry

QR-code based access control and visitor management for NIELIT Ropar, built with Flask.

## Features
- NIELIT-branded UI with logo and background image
- Register users and generate secure QR access passes
- Gate scanner with IN/OUT tracking (camera or image upload)
- Manual visitor log with host name and ID proof capture
- Admin dashboard — password protected, auto-logout on tab switch
- Day-wise CSV exports (entry register & visitor log) with date picker
- Role-separated navigation: scanner / admin / general areas isolated

## Quick Start

```bash
git clone <your-repo>
cd smart-entry-production
cp .env.example .env        # set SECRET_KEY and ADMIN_PASSWORD
pip install -r requirements.txt
python run.py               # visit http://localhost:5000
```

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

## Production (Gunicorn)

```bash
gunicorn -c gunicorn.conf.py run:app
```

## Docker

```bash
cp .env.example .env
docker compose up -d
```

## Key Endpoints

| Endpoint | Description |
|---|---|
| `/api/v1/portal/` | User registration & QR pass |
| `/api/v1/gate/` | Gate scanner terminal |
| `/api/v1/manual/` | Visitor log |
| `/api/v1/admin/dashboard-ui` | Admin dashboard (password protected) |
| `/health` | Health check |

