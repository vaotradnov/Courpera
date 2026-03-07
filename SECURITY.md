# Security Posture

This repository applies a pragmatic, defense‑in‑depth approach:

- Content Security Policy: strict defaults, Swagger/Redoc allowed via sidecar assets and a scoped hash for /docs.
- Passwords: Argon2 preferred; strengthened password validators.
- Authentication: sensible defaults for redirects; throttles on API endpoints to reduce abuse.
- Observability: request/user IDs in logs; health/readiness/metrics endpoints for liveness and monitoring.
- Static analysis: Bandit runs in pre‑commit and CI (Medium severity & confidence) and fails the lint job on findings. pip‑audit runs to check dependencies.
- Secrets hygiene: detect‑secrets baseline is enforced in pre‑commit.

Exceptions and error handling
- WebSocket and observability paths use best‑effort broadcasting and metrics; failures in these non‑critical paths never block user flows.
- Where broad exceptions are used to guarantee non‑critical resilience, they are limited to narrow scopes; future refactors should prefer targeted exceptions.

Reporting
- Please open issues in the private course repository with clear reproduction steps. Do not include secrets or private data.
