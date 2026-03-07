# Courpera

Courpera is a server-rendered e-learning web application built with Django. It provides user accounts (students and teachers), course authoring and enrolment, materials upload, course feedback, status updates, notifications, search, and real-time messaging.

Quickstart
- Create venv and install:
  - Windows PowerShell:
    - `python -m venv .venv`
    - `.venv\\Scripts\\Activate.ps1`
    - `pip install -r requirements.txt`
  - macOS/Linux:
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
    - `pip install -r requirements.txt`
- Run dev server:
  - `python manage.py migrate`
  - `python manage.py runserver`
- Verify:
  - `GET /healthz` → 200 `ok`
  - `GET /readyz` → JSON with `{"database": true, "redis": ...}` when `REDIS_URL` is set
  - `GET /metrics` → Prometheus text (counters present)
  - `GET /api/schema/` and open `/docs` and `/redoc`

Key Features
- User accounts and roles (students/teachers)
- Courses and enrolments with role-based access
- Materials upload with server-side validation
- Course feedback (rating and comments) and status updates
- Notifications (recent popover and full list)
- Search for people and courses
- Real-time messaging via WebSockets (course rooms and direct messages)
- REST API with OpenAPI documentation

Technology Stack
- Python and Django (server-rendered templates and forms)
- Django REST Framework (versioned REST API)
- drf-spectacular (OpenAPI/Swagger/Redoc)
- Django Channels + Redis (WebSockets)
- SQLite by default; WhiteNoise for static files
- Optional enhancements: HTMX for progressive enhancement, DiceBear avatars, Google reCAPTCHA v3 on registration, and iCalendar (ICS) export for events

Design & Accessibility
- Accessible, semantic HTML with a lightweight design system (CSS tokens and base styles)

UI Overhaul (Stage 14)
- Direction: Coursera-inspired information architecture and visual patterns while remaining brand-neutral.
- Header & Navigation: prominent global search; an "Explore" menu for subjects; clear CTAs (Join/Enrol); profile menu and notifications grouped to the right.
- Course Cards: responsive grid; card shows title, partner logo/name, instructor, rating, level, language/subtitles; consistent spacing and hover states; keyboard focus ring.
- Course Detail: hero panel with course title, partner, outcomes, flexible deadlines badge, and primary "Enrol for free" CTA; syllabus as an accordion; instructor section and FAQs below; sticky CTA on mobile.
- Filters & Discovery: facets for subject, level, language, duration with clear chips and reset.
- Components: buttons (primary/secondary/link), inputs, toasts/messages, popovers (notifications), accordions (syllabus), skeleton loaders.
- Design Tokens (examples):
  - Colours: --cp-colour-primary: #2A73CC; --cp-colour-accent: #1264A3; neutrals #111/#444/#777/#EEE; success/warn/error palette.
  - Spacing: 4/8/12/16/24/32 px scale; radii 4/8; shadows for elevation 1-3.
  - Typography: system UI stack (Segoe UI, Roboto, Helvetica, Arial, sans-serif); line-height 1.5; headings scaled down on mobile.
  - Breakpoints: 480 / 768 / 1024 / 1280 px.
- Accessibility: skip-link, landmark roles, labelled controls, visible focus; nav/menus/accordions ARIA attributes; keyboard operation of search and menus.
- CSP: no inline scripts/styles; all assets served from static/; connect-src allows ws/wss; img-src allows DiceBear and data:.

CI And Tests
- CI workflow `CI` runs in two jobs:
  - `test-fast`: runs `pytest -m "not slow"` with coverage gate 80% and uploads HTML/XML artifacts.
  - `test-slow`: runs only `pytest -m slow` (longer pagination/budget tests).
  - `lint`: runs Ruff (lint/format check) and MyPy (loose type checks) before tests.
  - Security: Bandit runs via pre-commit and as a standalone step (advisory, medium severity & confidence).
- Local equivalents:
  - Fast: `pytest -m "not slow" -vv -ra`
  - Slow: `pytest -m slow -vv -ra`
- Coverage gate is enforced at 86% (see `pytest.ini`).

 Security Scans
- Bandit (static security):
  - Pre-commit: `pre-commit run bandit --all-files`
  - Standalone: `bandit -r . -c bandit.yaml --severity-level medium --confidence-level medium`

Deploy
- Environment variables:
  - `DJANGO_SECRET_KEY`: strong secret key (required in prod).
  - `DJANGO_ALLOWED_HOSTS`: comma-separated hosts (e.g., `example.com,www.example.com`).
  - `DEBUG`: set to `false` in production.
  - `REDIS_URL`: `redis://host:port/0` to enable Channels Redis layer (optional; in-memory used otherwise).
  - `AVATAR_BASE_URL`, `AVATAR_STYLE`, `AVATAR_SEED_SALT`: optional avatar tuning.
- Static files: run `python manage.py collectstatic` and serve via WhiteNoise or your web server.
- Database: SQLite by default; can switch to Postgres by setting `DATABASES` in a custom settings module.
- Running:
  - `DJANGO_SETTINGS_MODULE=config.settings.prod gunicorn config.wsgi:application` for WSGI.
  - `daphne -b 0.0.0.0 -p 8000 config.asgi:application` for ASGI (WebSockets support).

Health/Readiness and Metrics
- Endpoints:
  - `/healthz`: liveness probe; returns plain `ok` with 200.
  - `/readyz`: readiness probe; verifies database connectivity. If the `REDIS_URL` env var is set, also attempts a Redis `PING` and includes a `{"redis": true|false}` key. Returns 200 only when the database is reachable and Redis (if configured) is not failing; otherwise returns 503.
  - `/metrics`: Prometheus text format counters:
    - `courpera_notifications_created_total`
    - `courpera_ws_notif_push_total`
    - `courpera_messages_created_total` (incremented on both WebSocket and HTTP message creation paths)
    - `courpera_http_responses_total_2xx|3xx|4xx|5xx`

Verification
- Run: `pytest -m "not ws"` for quick UI smoke; `pytest -m security` for CSP/permissions.
- Manual: compare header/search prominence, Explore menu, card grid, hero CTA, syllabus accordion against Coursera's layout patterns.

GitHub Actions Badges (optional)
- Replace `OWNER/REPO` with your repo to enable badges:
  - Fast job badge: `![CI (fast)](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)`
  - Slow job badge: same workflow badge (shows overall status). If you need per-job badges, use a matrix/summary action or separate workflows.
Developer Tooling
- Pre-commit: install hooks with `pre-commit install` to run Ruff/format/MyPy on changed files.
- Ruff: `ruff check . && ruff format --check .` (use `--fix` to apply safe fixes).
- MyPy: `mypy --config-file mypy.ini .` (baseline: ignore missing imports; tighten over time).
- Security: consider running `pip-audit` or `safety check` regularly; Bandit (narrow ruleset) can be added if desired.
