from __future__ import annotations

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
    data = {"database": db_ok}
    status = 200 if db_ok else 503
    return JsonResponse(data, status=status)
