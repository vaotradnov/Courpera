from __future__ import annotations

import re
from datetime import timedelta

from assignments.services import (
    deadline_delta_for_key,
    parse_widget_local_datetime,
    widget_now_string,
)


def test_widget_now_string_format():
    s = widget_now_string()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", s)


def test_deadline_delta_mapping_and_parse_roundtrip():
    assert deadline_delta_for_key("1w") == timedelta(weeks=1)
    assert deadline_delta_for_key("3m") == timedelta(days=90)
    # Round-trip parse of a simple value
    s = "2026-03-05T10:15"
    dt = parse_widget_local_datetime(s)
    # It returns an aware datetime in current TZ
    assert dt is not None and getattr(dt, "tzinfo", None) is not None
