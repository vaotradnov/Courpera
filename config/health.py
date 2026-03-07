from __future__ import annotations

import os

from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


def readyz(request: HttpRequest) -> JsonResponse:
    db_ok = True
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:
        db_ok = False
    # Optional Redis readiness (non-fatal when REDIS_URL is unset)
    redis_url = os.environ.get("REDIS_URL", "").strip()
    redis_ok = None
    if redis_url:
        try:  # pragma: no cover - depends on local environment
            import redis  # type: ignore

            r = redis.from_url(redis_url, socket_timeout=0.2)
            r.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
    data = {"database": db_ok}
    if redis_ok is not None:
        data["redis"] = redis_ok
    # In development, allow Redis failure without failing readiness
    if settings.DEBUG:
        status = 200 if db_ok else 503
    else:
        status = 200 if db_ok and (redis_ok is not False) else 503
    return JsonResponse(data, status=status)
