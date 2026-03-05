from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def time_until(dt):
    """Return a compact relative time until the given datetime.

    Examples: '2d', '3h 15m', or '0m' when within a minute or past.
    """
    if not dt:
        return ""
    try:
        now = timezone.now()
        delta = dt - now
        seconds = int(delta.total_seconds())
        if seconds <= 0:
            return "0m"
        minutes = seconds // 60
        days, rem_mins = divmod(minutes, 1440)
        hours, mins = divmod(rem_mins, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if not days and mins and hours < 6:
            parts.append(f"{mins}m")
        if not parts:
            parts.append("0m")
        return " ".join(parts)
    except Exception:
        return ""


@register.filter
def filesize(num):
    """Human-readable file size (B/KB/MB/GB)."""
    try:
        n = float(num or 0)
    except Exception:
        n = 0.0
    units = ["B", "KB", "MB", "GB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.1f} {units[i]}"
