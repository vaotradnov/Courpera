from __future__ import annotations

import hashlib

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def avatar_url(user, size: int = 48) -> str:
    """Return a deterministic DiceBear avatar URL for a user.

    Uses user.pk and a salt; does not expose e‑mail/username.
    """
    try:
        # Prefer uploaded avatar if present
        prof = getattr(user, "profile", None)
        if prof and getattr(prof, "avatar", None) and getattr(prof.avatar, "url", ""):
            return prof.avatar.url
        # Role-specific static default; keep deterministic query (size + seed)
        role = getattr(getattr(user, "profile", None), "role", "student")
        img = "avatar-teacher.svg" if role == "teacher" else "avatar-default.svg"
        seed_src = (
            f"{getattr(user, 'pk', '0')}:{getattr(settings, 'AVATAR_SEED_SALT', 'courpera')}:{role}"
        )
        seed = hashlib.sha256(seed_src.encode()).hexdigest()
        return f"/static/img/{img}?size={size}&seed={seed}"
    except Exception:
        return ""
