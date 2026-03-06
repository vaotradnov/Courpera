# Contributing

Thanks for contributing to Courpera! This guide keeps quality high and reviews fast.

## Pull Requests
- Write small, focused PRs with a clear goal and scope.
- Include tests for fixes and new behaviour.
- Keep comments brief, helpful, and in Canadian English.
- Avoid restating the code; explain why, not what.

## Local Workflow
1. Create and activate a virtualenv.
2. Install deps: `pip install -r requirements.txt`.
3. Run hooks: `pre-commit install`.
4. Lint/format: `ruff check . && ruff format --check .`.
5. Types: `mypy --config-file mypy.ini .`.
6. Tests: `pytest -m "not slow"` (and `pytest -m slow` when relevant).

## Comments & Docstrings
- Keep module/class/function docstrings to a one‑line summary where possible.
- Prefer short, imperative comments (e.g., “Guard against open redirect”).
- Use “internationalisation”, “enrol/enrolment”, and “email”.

## Security & Privacy
- Validate `next`/redirect params via `safe_next_url`.
- Keep CSP compliant with no inline scripts/styles.
- Do not log secrets or PII; redact on error paths.

## Migrations
- If models change, include migrations and ensure `manage.py makemigrations --check --dry-run` passes in CI.

## CI
- Lint (Ruff), format check, MyPy, dependency audit, tests (fast/slow) with 86% coverage gate.
