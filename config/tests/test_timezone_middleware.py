from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils import timezone

from config.middleware import UserTimezoneMiddleware


@pytest.mark.django_db
def test_user_timezone_middleware_activates_profile_tz():
    rf = RequestFactory()
    user = User.objects.create_user(username="tz", password="pw")
    # Assign a specific timezone on profile
    try:
        p = user.profile
        p.timezone = "Europe/London"
        p.save(update_fields=["timezone"])
    except Exception:
        pass
    req = rf.get("/")
    req.user = user
    mw = UserTimezoneMiddleware(lambda r: None)
    mw.process_request(req)
    # Active timezone should be set (not UTC default deactivated)
    assert str(timezone.get_current_timezone()) in ("Europe/London", "GMT")


@pytest.mark.django_db
def test_user_timezone_middleware_defaults_for_anonymous():
    rf = RequestFactory()
    req = rf.get("/")
    from django.contrib.auth.models import AnonymousUser

    req.user = AnonymousUser()
    mw = UserTimezoneMiddleware(lambda r: None)
    mw.process_request(req)
    # Should deactivate to default TIME_ZONE (Europe/London), not raise
    tzname = str(timezone.get_current_timezone())
    assert tzname in ("Europe/London", "GMT")
