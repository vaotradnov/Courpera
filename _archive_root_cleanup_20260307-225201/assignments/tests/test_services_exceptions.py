from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import pytest

from assignments.services import (
    parse_widget_local_datetime,
    resolve_base_time_from_post_or_instance,
    update_attempts_allowed_if_safe,
)


def test_parse_widget_local_datetime_invalid_returns_none() -> None:
    assert parse_widget_local_datetime("not-a-datetime") is None


def test_update_attempts_allowed_if_safe_invalid_input_short_circuits() -> None:
    # Passing a non-int string triggers the ValueError branch and returns False
    assert update_attempts_allowed_if_safe(assignment=None, new_attempts="oops") is False  # type: ignore[arg-type]


class BadMapping(Mapping[str, Any]):
    def __getitem__(self, k: str) -> Any:  # pragma: no cover - not used
        raise RuntimeError("not used")

    def __iter__(self):  # pragma: no cover - not used
        return iter(())

    def __len__(self) -> int:  # pragma: no cover - not used
        return 0

    def get(self, key: str, default: Any = None) -> Any:
        # Trigger the exception branch in resolver
        raise ValueError("boom")


def test_resolve_base_time_handles_mapping_get_exception() -> None:
    base = resolve_base_time_from_post_or_instance(BadMapping(), object())
    assert isinstance(base, datetime)
