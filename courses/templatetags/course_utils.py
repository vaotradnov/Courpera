from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def filesize(num: int) -> str:
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

