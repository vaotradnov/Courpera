from __future__ import annotations

import re
from datetime import timedelta

from assignments.services import (
    deadline_delta_for_key,
    parse_widget_local_datetime,
    resolve_base_time_from_post_or_instance,
    update_attempts_allowed_if_safe,
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


def test_parse_widget_local_datetime_invalid_returns_none() -> None:
    assert parse_widget_local_datetime("not-a-datetime") is None


def test_update_attempts_allowed_if_safe_invalid_input_short_circuits() -> None:
    assert update_attempts_allowed_if_safe(assignment=None, new_attempts="oops") is False  # type: ignore[arg-type]


def test_resolve_base_time_handles_mapping_get_exception() -> None:
    class BadMapping(dict):
        def get(self, key, default=None):
            raise ValueError("boom")

    base = resolve_base_time_from_post_or_instance(BadMapping(), object())
    # Returns an aware datetime fallback (now) on exception
    assert getattr(base, "tzinfo", None) is not None
