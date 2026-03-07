from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from .models import Message, Room
from .services import notify_message_by_id


def get_room_slow_mode(room_id: int) -> int:
    """Return active slow-mode seconds for a room; auto-clear if expired."""
    try:
        r = Room.objects.only("slow_mode_seconds", "slow_mode_expires_at").get(pk=room_id)
    except Room.DoesNotExist:
        return 0
    secs = int(r.slow_mode_seconds or 0)
    if secs and r.slow_mode_expires_at and timezone.now() >= r.slow_mode_expires_at:
        r.slow_mode_seconds = 0
        r.slow_mode_expires_at = None
        r.save(update_fields=["slow_mode_seconds", "slow_mode_expires_at"])
        return 0
    return secs


def create_delayed_message(
    room_id: int, user_id: int, text: str, parent_id: int | None, delay_secs: int
) -> int:
    """Persist a message scheduled for future publication and return its id."""
    if len(text) > 500:
        text = text[:500]
    vis = timezone.now() + timedelta(seconds=max(1, int(delay_secs)))
    m = Message.objects.create(
        room_id=room_id, sender_id=user_id, text=text, parent_message_id=parent_id, visible_at=vis
    )
    return m.id


def fetch_and_publish_due(room_id: int, limit: int = 20) -> List[Dict]:
    """Publish due messages and return payloads to broadcast."""
    now = timezone.now()
    with transaction.atomic():
        ids = list(
            Message.objects.select_for_update(skip_locked=True)
            .filter(room_id=room_id, published_at__isnull=True, visible_at__lte=now)
            .order_by("visible_at", "id")
            .values_list("id", flat=True)[:limit]
        )
        if not ids:
            return []
        Message.objects.filter(id__in=ids, published_at__isnull=True).update(published_at=now)
        rows = (
            Message.objects.filter(id__in=ids).select_related("sender").order_by("visible_at", "id")
        )
        out: list[dict] = []
        for m in rows:
            # Create in-app notifications for matured messages (best-effort)
            try:
                notify_message_by_id(m.id)
            except Exception:
                pass
            out.append(
                {
                    "type": "message.new",
                    "id": m.id,
                    "sender": getattr(m.sender, "username", ""),
                    "message": m.text,
                    "created_at": m.created_at.isoformat(),
                    "parent_id": m.parent_message_id,
                }
            )
        return out


def mark_published(message_id: int) -> None:
    """Mark a message as published if not already."""
    Message.objects.filter(id=message_id, published_at__isnull=True).update(
        published_at=timezone.now()
    )


# Presence bookkeeping (in-memory, per-process; suitable for dev/tests)
_presence: dict[int, set[int]] = {}


def presence_add(room_id: int, user_id: int) -> set[int]:
    s = _presence.setdefault(room_id, set())
    s.add(user_id)
    return set(s)


def presence_remove(room_id: int, user_id: int) -> set[int]:
    s = _presence.get(room_id)
    if s and user_id in s:
        s.remove(user_id)
    return set(s or set())


def presence_get(room_id: int) -> set[int]:
    return set(_presence.get(room_id, set()))
