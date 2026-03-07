from __future__ import annotations

import logging

from config.obsv import RequestContextFilter, request_id_var, user_id_var


def test_request_context_filter_sets_request_and_user_ids():
    # Arrange context
    request_id_var.set("abc-123")
    user_id_var.set(42)
    # Log record without those attributes
    rec = logging.LogRecord("test", logging.INFO, __file__, 0, "msg", args=(), exc_info=None)
    f = RequestContextFilter()
    assert f.filter(rec) is True
    assert getattr(rec, "request_id") == "abc-123"
    assert getattr(rec, "user_id") == 42


def test_request_context_filter_handles_exception(monkeypatch):
    # Force an exception during context access to exercise fallback path
    class Dummy:
        def get(self):  # type: ignore[no-redef]
            raise RuntimeError("boom")

    monkeypatch.setattr("config.obsv.request_id_var", Dummy())
    rec = logging.LogRecord("test", logging.INFO, __file__, 0, "msg", args=(), exc_info=None)
    f = RequestContextFilter()
    assert f.filter(rec) is True
    # Fallback values are strings with "-"
    assert getattr(rec, "request_id") == "-"
    assert getattr(rec, "user_id") == "-"
