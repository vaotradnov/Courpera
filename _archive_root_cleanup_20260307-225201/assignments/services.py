from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from typing import Optional

from django.utils import timezone


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
