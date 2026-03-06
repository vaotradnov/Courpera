from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, tzinfo
from typing import Any, Mapping, Optional

from django.utils import timezone

from .models import Assignment, Attempt


def widget_now_string(tz: Optional[tzinfo] = None) -> str:
    tz = tz or timezone.get_current_timezone()
    return timezone.localtime(timezone.now(), tz).strftime("%Y-%m-%dT%H:%M")


def deadline_delta_for_key(key: str) -> Optional[timedelta]:
    mapping = {
        "1d": timedelta(days=1),
        "3d": timedelta(days=3),
        "1w": timedelta(weeks=1),
        "2w": timedelta(weeks=2),
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
    }
    return mapping.get((key or "").strip())


def parse_widget_local_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse `YYYY-MM-DDTHH:MM` and return an aware datetime in current TZ.

    Returns None if parsing fails or value is falsy.
    """
    if not value:
        return None
    try:
        naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return timezone.make_aware(naive, timezone.get_current_timezone())
    except Exception:
        return None


def update_attempts_allowed_if_safe(assignment: Assignment, new_attempts: int | str | None) -> bool:
    """Update attempts if >= used and >= 1; return True when updated.

    Does not lower below attempts already used. Returns False on no-op or invalid.
    """
    try:
        if new_attempts is None:
            return False
        new_attempts = int(new_attempts)
    except Exception:
        return False
    if new_attempts < 1:
        return False
    # Guard against lowering below any student's attempts used.
    # Use an order_by/first pattern instead of aggregate(Max("c")) to
    # avoid mypy/django-stubs plugin crashes on some environments.
    try:
        ids = list(
            Attempt.objects.filter(assignment=assignment).values_list("student_id", flat=True)
        )
        used_max = max(Counter(ids).values(), default=0)
    except Exception:
        used_max = 0
    if new_attempts >= used_max and new_attempts != assignment.attempts_allowed:
        assignment.attempts_allowed = new_attempts
        assignment.save(update_fields=["attempts_allowed"])
        return True
    return False


def resolve_base_time_from_post_or_instance(
    post_data: Mapping[str, Any] | None, instance: Any
) -> datetime:
    """Resolve a base datetime from POST or instance available_from.

    - If POST contains a valid widget-local "available_from", use it.
    - Else fall back to instance.available_from.
    - Else current time (timezone-aware).
    """
    base = None
    try:
        base = parse_widget_local_datetime((post_data or {}).get("available_from"))
    except Exception:
        base = None
    if not base:
        base = getattr(instance, "available_from", None) or timezone.now()
    return base
