from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from activity.models import Notification
from config.metrics import inc as metrics_inc
from courses.models import Enrolment

from .models import Message, Room, RoomMembership


@dataclass
class _Recipients:
    user_ids: Sequence[int]
    course_id: int | None = None


def _recipients_for_message(m: Message) -> _Recipients:
    room = m.room
    if room.kind == Room.KIND_COURSE:
        if not room.course_id:
            return _Recipients(user_ids=[])
        # Owner + enrolled students (exclude sender)
        owner_id = room.course.owner_id if room.course else None
        enrolled = list(
            Enrolment.objects.filter(course_id=room.course_id).values_list("student_id", flat=True)
        )
        ids = [uid for uid in enrolled if uid and uid != m.sender_id]
        if owner_id and owner_id != m.sender_id:
            ids.append(owner_id)
        # De-duplicate
        ids = sorted(set(ids))
        return _Recipients(user_ids=ids, course_id=room.course_id)
    else:
        # Group/DM members (exclude banned and sender)
        ids = list(
            RoomMembership.objects.filter(room_id=room.id, banned=False)
            .exclude(user_id=m.sender_id)
            .values_list("user_id", flat=True)
        )
        return _Recipients(user_ids=ids)


def _format_message(m: Message) -> str:
    sender = getattr(m.sender, "username", "Someone")
    text = (m.text or "").strip()
    snippet = (text[:40] + ("..." if len(text) > 40 else "")) if text else "New message"
    base = "Chat"
    if m.room.kind == Room.KIND_COURSE:
        base = "Course chat"
    elif m.room.kind == Room.KIND_GROUP:
        base = "Group chat"
    elif m.room.kind == Room.KIND_DM:
        base = "Direct chat"
    return f"{base}: {sender}: {snippet}"


def create_chat_notifications_for_message(m: Message) -> int:
    """Create in-app notifications for a chat message.

    Returns the number of notifications created. Respects NOTIFICATIONS_IN_APP_ENABLED.
    """
    if not getattr(settings, "NOTIFICATIONS_IN_APP_ENABLED", True):
        return 0
    rec = _recipients_for_message(m)
    if not rec.user_ids:
        return 0
    msg = _format_message(m)
    now = timezone.now()
    # Build Notification rows
    rows: list[Notification] = []
    for uid in rec.user_ids:
        rows.append(
            Notification(
                user_id=uid,
                actor_id=m.sender_id,
                type=Notification.TYPE_CHAT,
                course_id=rec.course_id,
                message=msg,
                created_at=now,
            )
        )
    Notification.objects.bulk_create(rows, ignore_conflicts=True)
    try:
        metrics_inc("courpera_notifications_created_total", len(rows))
    except Exception:
        pass
    try:
        logging.getLogger("courpera.notifications").info(
            "notif.create count=%s room_id=%s course_id=%s sender_id=%s",
            len(rows),
            m.room_id,
            rec.course_id,
            m.sender_id,
        )
    except Exception:
        pass
    # Push real-time badge bumps to recipients
    try:
        layer = get_channel_layer()
        for uid in rec.user_ids:
            async_to_sync(layer.group_send)(
                f"user_{uid}_notifications",
                {"type": "notif_message", "payload": {"type": "notif.bump", "delta": 1}},
            )
        try:
            metrics_inc("courpera_ws_notif_push_total", len(rec.user_ids))
        except Exception:
            pass
    except Exception:
        pass
    return len(rows)


def notify_message_by_id(message_id: int) -> int:
    m = (
        Message.objects.select_related("room", "room__course", "sender")
        .only(
            "id",
            "text",
            "sender__username",
            "sender_id",
            "room_id",
            "room__kind",
            "room__course_id",
        )
        .get(pk=message_id)
    )
    return create_chat_notifications_for_message(m)
