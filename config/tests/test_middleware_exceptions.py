from __future__ import annotations

from django.http import HttpResponse

from config.middleware import (
    RequestIDMiddleware,
    ResponseMetricsMiddleware,
    UserTimezoneMiddleware,
)


class _NoMetaReq:
    # Deliberately minimal object without META
    pass


def test_request_id_middleware_process_request_handles_missing_meta():
    mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
    # Should not raise even if request lacks META
    mw.process_request(_NoMetaReq())


def test_request_id_middleware_process_response_handles_missing_meta():
    mw = RequestIDMiddleware(lambda r: HttpResponse("ok"))
    resp = HttpResponse("ok")
    out = mw.process_response(_NoMetaReq(), resp)
    assert out is resp


class _BadProfileUser:
    is_authenticated = True

    @property
    def profile(self):  # pragma: no cover - we want the exception path in middleware
        raise RuntimeError("boom")


class _ReqWithUser:
    def __init__(self):
        self.user = _BadProfileUser()


def test_user_timezone_middleware_handles_profile_exception():
    mw = UserTimezoneMiddleware(lambda r: HttpResponse("ok"))
    # Ensure no exceptions bubble up
    mw.process_request(_ReqWithUser())


class _BadStatusResponse:
    @property
    def status_code(self):  # pragma: no cover - we want middleware except
        raise RuntimeError("boom")


def test_response_metrics_middleware_handles_exceptions():
    mw = ResponseMetricsMiddleware(lambda r: HttpResponse("ok"))
    out = mw.process_response(_NoMetaReq(), _BadStatusResponse())
    assert out is not None
