from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from assignments.templatetags.assign_utils import time_until


def test_time_until_formats_future_and_past():
    now = timezone.now()
    assert time_until(None) == ""
    assert time_until(now - timedelta(minutes=1)) == "0m"
    # ~3 hours, 15 minutes
    s = time_until(now + timedelta(hours=3, minutes=15))
    # Allow 14–16 minutes due to second boundary rounding
    assert "3h" in s and any(m in s for m in ("14m", "15m", "16m"))
    # 2 days -> '2d'
    s2 = time_until(now + timedelta(days=2, hours=1))
    assert s2.startswith("2d")
