from __future__ import annotations

import logging
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        try:
            rid = request_id_var.get()
            uid = user_id_var.get()
            setattr(record, "request_id", rid or "-")
            setattr(record, "user_id", uid if uid is not None else "-")
        except Exception:
            setattr(record, "request_id", "-")
            setattr(record, "user_id", "-")
        return True
