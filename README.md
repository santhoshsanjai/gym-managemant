# Gym Management System

A responsive web app / PWA for running a single gym: members, trainers, packages,
subscriptions, QR-based attendance, manual payments, monthly Excel reports and
subscription-expiry reminders. Two roles: **Admin** and **Member**.

| Layer | Tech |
| --- | --- |
| Frontend | Angular 22 (standalone components, signals, zoneless), installable PWA |
| Backend | FastAPI, SQLAlchemy 2, Alembic, APScheduler, OpenPyXL |
| Database | PostgreSQL 16 |
| Auth | JWT bearer tokens, Argon2id password hashing, role-based access on every endpoint |
| Deploy | Docker Compose: PostgreSQL, API, web, Nginx (HTTPS via Let's Encrypt) |

```
backend/            FastAPI modular monolith (one package per business domain)
  app/auth          login, JWT, roles, password change
  app/members       member profiles, account status, member self-service
  app/trainers      trainer records
  app/packages      package catalogue
  app/subscriptions assignments, renewals, derived state (upcoming/active/expired)
  app/attendance    rotating QR tokens, check-in rules, attendance records
  app/payments      manual payment records and monthly summaries
  app/dashboard     Admin and Member dashboards
  app/reports       .xlsx exports
  app/notifications reminder job, in-app notifications, optional Web Push
  app/common        config, DB session, security, audit log, rate limiting
  alembic/          migrations
  tests/            pytest suite (runs against PostgreSQL)
frontend/           Angular app (admin screens, member screens, QR scanner, QR display)
deploy/             Nginx edge config, backup script
```

## Running locally

Prerequisites: Python 3.12+, Node 22+, PostgreSQL 16.

```bash
# Database
createuser -P gym          # password: gym
createdb -O gym gym

# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env       # adjust if needed
alembic upgrade head
python -m app.cli seed-demo            # optional demo data (admin / admin12345)
uvicorn app.main:app --reload          # http://localhost:8000/api/docs

# Frontend (separate terminal)
cd frontend
npm install
npm start                               # http://localhost:4200 (proxies /api to :8000)
```

Create a real admin with `python -m app.cli create-admin <username>`.

### Tests

```bash
cd backend && createdb -O gym gym_test && pytest     # 31 API tests on PostgreSQL
cd frontend && npx ng test --watch=false             # unit tests
```

CI (`.github/workflows/ci.yml`) runs lint, both test suites and a production build on every PR.

## How attendance works

1. The Admin opens **Gym QR display** (`/admin/qr-display`) on a tablet or screen at the entrance.
   It shows a QR code holding a random, server-issued token that rotates every 60 seconds.
2. The member opens **Check in** in the app, which uses the phone camera (HTTPS required) to read the code.
3. The API validates the token (unknown or expired tokens are rejected), the member's account,
   their subscription and the per-day limit, then records attendance with the **server's** time.
   The device clock is never used. Check-ins for the same member are serialised with a row lock,
   so double taps can't create duplicates.

Admins can also record attendance manually (for example, when a member's camera is broken).

## Client decisions (scope section 13): defaults used

All of these are environment settings (see `backend/.env.example`), so the gym can change them without code changes.

| # | Decision | Default implemented | Setting |
| --- | --- | --- | --- |
| 1 | Web app/PWA or native | Responsive Angular PWA | — |
| 2 | Who scans | Member scans a rotating gym-displayed QR | `QR_TOKEN_TTL_SECONDS`, `QR_TOKEN_GRACE_SECONDS` |
| 3 | Business-day time zone / cutoff | Asia/Kolkata, day starts at midnight | `GYM_TIMEZONE`, `GYM_DAY_START_HOUR` |
| 4 | Check-ins per day | One per member per gym day | `ATTENDANCE_MAX_CHECKINS_PER_DAY` (0 = unlimited) |
| 5 | Block expired/suspended members | Yes; inactive accounts are always blocked | `ATTENDANCE_REQUIRE_ACTIVE_SUBSCRIPTION` |
| 6 | Reminder schedule | 7 days and 1 day before expiry, plus an "expired" notice; runs daily at 08:00 gym time | `REMINDER_DAYS_BEFORE_EXPIRY`, `REMINDER_RUN_HOUR` |
| 7 | Member-editable fields | email, address, gender, date of birth, photo URL | `MEMBER_EDITABLE_FIELDS` |
| 8 | Payment methods / statuses | cash, UPI, card, bank transfer, cheque, other / paid, pending, failed, refunded | code enums |
| 9 | Monthly Excel columns | Payment, member, trainer, package and subscription details; paid only by default; summary sheet | report filter |
| 10 | Target browsers | Any current browser with camera API over HTTPS; verify on the gym's phones | — |

Other rules worth knowing:

- **Expiry date is inclusive** (the last day the member may train). A 1-month package from 15 Nov ends on 14 Dec.
- **Renewals create a new subscription** linked to the previous one; history is never overwritten.
  By default a renewal starts the day after the current period ends (or today if it already lapsed).
  Overlapping active subscriptions for the same member are rejected.
- Package edits don't change existing subscriptions (name, duration and price are snapshotted).
  Deactivated packages can't be assigned.
- **Active members** = account active and a subscription covers today. **Expired members** = had a
  subscription but none covers today. **Monthly revenue** = sum of `paid` payments by payment date.
- Payments are never deleted; correct them or mark them failed/refunded. Trainers with assigned members
  can only be deactivated, not deleted.
- New members get an Admin-set initial password and must change it on first sign-in.
  There is no self-service email reset in this release; the Admin resets passwords.
- Important Admin actions are written to an audit log (`GET /api/audit-logs`).
- Login and check-in are rate limited in the API and again at Nginx.

## Deployment (Linux VPS)

```bash
git clone <repo> /opt/gym && cd /opt/gym
cp .env.example .env                 # set DOMAIN, passwords, JWT_SECRET
# Get a certificate once (port 80 must be free):
docker run --rm -p 80:80 -v $PWD/deploy/certbot/conf:/etc/letsencrypt certbot/certbot \
  certonly --standalone -d "$DOMAIN" --agree-tos -m you@example.com -n
docker compose up -d --build
```

- The API container applies migrations on start, then serves on port 8000 behind Nginx.
- Renew certificates with `certbot renew --webroot -w deploy/certbot/www` from cron, then `docker compose exec proxy nginx -s reload`.
- Backups: `deploy/backup.sh` (daily `pg_dump`, 14-day retention). Instructions for a restore test are in the script.
- Web Push is optional: set `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`. In-app notifications always work.

API documentation is served at `/api/docs` (Swagger UI) and `/api/redoc`.

## Out of scope for this release

Online payments, trainer logins, workout/diet plans, progress tracking, multi-branch, and app-store publishing (see scope section 12).
