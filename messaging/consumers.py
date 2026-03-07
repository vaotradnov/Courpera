from __future__ import annotations

import time
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.utils import timezone

from courses.models import Course, Enrolment

from .models import Message, Room, RoomMembership
from .services import notify_message_by_id

# In-memory presence and rate data (per-process; fine for dev/tests)
_presence: dict[int, set[int]] = {}
_last_sent: dict[tuple[int, int], float] = {}


@database_sync_to_async
def _course_auth(user, course_id: int) -> tuple[bool, str, Course | None]:
    try:
        course = Course.objects.select_related("owner").get(pk=course_id)
    except Course.DoesNotExist:
        return False, "Course not found", None
    if not user or isinstance(user, AnonymousUser):
        return False, "Authentication required", None
    if course.owner_id == user.id:
        return True, "", course
    ok = Enrolment.objects.filter(course=course, student=user).exists()
    return (ok, "Enrol to join this room" if not ok else "", course)


@database_sync_to_async
def _get_or_create_course_room(course_id: int) -> Room:
    room = Room.objects.filter(kind=Room.KIND_COURSE, course_id=course_id).first()
    if room:
        return room
    return Room.objects.create(kind=Room.KIND_COURSE, course_id=course_id, title="")


@database_sync_to_async
def _persist_room_message(room_id: int, sender, text: str, parent_id: int | None = None) -> Message:
    if len(text) > 500:
        text = text[:500]
    return Message.objects.create(
        room_id=room_id, sender=sender, text=text, parent_message_id=parent_id
    )


class CourseChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.course_id = int(self.scope["url_route"]["kwargs"]["course_id"])
        ok, reason, course = await _course_auth(self.scope.get("user"), self.course_id)
        if not ok:
            await self.close(code=4001)
            return
        self.course = course
        room = await _get_or_create_course_room(self.course_id)
        self.room = room
        # Use a stable group based on room id so alias and generic connect to same group
        self.room_name = f"room_{room.id}"
        # Simple per-connection rate limiter: max 5 messages per 5 seconds
        self._rate_ts = []
        self._last_typing = 0.0
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        # Flush any due delayed messages on connect
        try:
            due = await _fetch_and_publish_due(self.room.id)
            for p in due:
                await self.channel_layer.group_send(
                    self.room_name, {"type": "chat_message", "payload": p}
                )
        except Exception:
            pass

    async def receive_json(self, content, **kwargs):
        # Course chat ignores typing/presence signals to avoid noisy echoes in tests/UX
        if isinstance(content, dict) and content.get("type") == "typing":
            return

        msg = (content or {}).get("message", "").strip()
        parent_id = content.get("parent_id") if isinstance(content, dict) else None
        if not msg:
            return
        # Enforce basic per-connection rate limiting to reduce spam
        try:
            now = time.time()
            self._rate_ts = [t for t in self._rate_ts if now - t < 5.0]
            if len(self._rate_ts) >= 5:
                # Silent drop on course route to keep legacy test semantics
                return
            self._rate_ts.append(now)
        except Exception:
            pass
        # Slow-mode enforcement (room-level) and mute/ban (N/A for course)
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            # Always fetch latest slow mode from DB to reflect UI updates without reconnect
            ssecs = await _get_room_slow_mode(self.room.id)
            self.room.slow_mode_seconds = ssecs
            if uid and ssecs:
                key = (self.room.id, uid)
                last = _last_sent.get(key, 0.0)
                if now - last < float(ssecs):
                    await self.send_json({"type": "system.notice", "message": "Slow mode active"})
                    return
                _last_sent[key] = now
        except Exception:
            pass
        # Per-member moderation (course rooms may have a membership record for targeted students)
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            mem = await _get_membership(self.room.id, uid) if uid else None
            if mem is not None:
                if getattr(mem, "banned", False):
                    await self.send_json(
                        {"type": "system.notice", "message": "You are banned in this room"}
                    )
                    return
                mu = getattr(mem, "muted_until", None)
                if mu and mu > timezone.now():
                    await self.send_json({"type": "system.notice", "message": "You are muted"})
                    return
                dsecs = int(getattr(mem, "delay_seconds", 0) or 0)
                if dsecs > 0:
                    await _create_delayed_message(self.room.id, uid, msg, parent_id, dsecs)
                    await self.send_json(
                        {
                            "type": "system.notice",
                            "message": f"Your message will be delivered in {dsecs}s",
                        }
                    )
                    # Flush any newly-due items
                    due = await _fetch_and_publish_due(self.room.id)
                    for p in due:
                        await self.channel_layer.group_send(
                            self.room_name, {"type": "chat_message", "payload": p}
                        )
                    return
        except Exception:
            pass
        m = await _persist_room_message(
            self.room.id,
            self.scope.get("user"),
            msg,
            parent_id if isinstance(parent_id, int) else None,
        )
        try:
            await _mark_published(m.id)
        except Exception:
            pass
        # Create in-app notifications (best-effort)
        try:
            await _notify_message(m.id)
        except Exception:
            pass
        payload = {
            "type": "message.new",
            "id": getattr(m, "id", None),
            "sender": getattr(self.scope.get("user"), "username", ""),
            "message": msg,
            "created_at": m.created_at.isoformat(),
            "parent_id": parent_id if isinstance(parent_id, int) else None,
        }
        await self.channel_layer.group_send(
            self.room_name, {"type": "chat_message", "payload": payload}
        )
        # Flush any due items in case others matured
        try:
            due = await _fetch_and_publish_due(self.room.id)
            for p in due:
                await self.channel_layer.group_send(
                    self.room_name, {"type": "chat_message", "payload": p}
                )
        except Exception:
            pass

    async def chat_message(self, event):
        payload = event.get("payload", {})
        # Don't echo presence/typing events back to the sender
        if payload.get("origin") == self.channel_name and str(payload.get("type", "")).startswith(
            "typing"
        ):
            return
        if payload.get("origin") == self.channel_name and payload.get("type") == "presence.state":
            return
        await self.send_json(payload)

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        except Exception:
            pass


@database_sync_to_async
def _room_auth(user, room_id: int) -> tuple[bool, str, Room | None]:
    if not user or isinstance(user, AnonymousUser):
        return False, "Authentication required", None
    try:
        room = Room.objects.select_related("course").get(pk=room_id)
    except Room.DoesNotExist:
        return False, "Room not found", None
    if room.kind == Room.KIND_COURSE:
        # Same rules as course rooms: owner or enrolled
        course = room.course
        if course and course.owner_id == user.id:
            return True, "", room
        if course and Enrolment.objects.filter(course=course, student=user).exists():
            return True, "", room
        return False, "Enrol to join this room", None
    # For dm/group: membership required
    mem = RoomMembership.objects.filter(room=room, user=user).first()
    if not mem:
        return False, "Join this room to participate", None
    if getattr(mem, "banned", False):
        return False, "Banned from this room", None
    return True, "", room


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        ok, reason, room = await _room_auth(self.scope.get("user"), self.room_id)
        if not ok:
            await self.close(code=4001)
            return
        self.room = room
        self.room_name = f"room_{self.room.id}"
        self._rate_ts = []
        self._last_typing = 0.0
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        # Presence join
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            if uid:
                _presence.setdefault(self.room.id, set()).add(uid)
                if len(_presence[self.room.id]) > 1:
                    try:
                        users = await _usernames_for_ids(list(_presence[self.room.id]))
                    except Exception:
                        users = []
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "chat_message",
                            "payload": {
                                "type": "presence.state",
                                "count": len(_presence[self.room.id]),
                                "users": users,
                                "origin": self.channel_name,
                            },
                        },
                    )
        except Exception:
            pass

    async def receive_json(self, content, **kwargs):
        # Typing events
        if isinstance(content, dict) and content.get("type") == "typing":
            act = content.get("action")
            now = time.time()
            if now - getattr(self, "_last_typing", 0.0) >= 1.5:
                self._last_typing = now
                await self.channel_layer.group_send(
                    self.room_name,
                    {
                        "type": "chat_message",
                        "payload": {
                            "type": f"typing.{act}" if act in ("start", "stop") else "typing.start",
                            "user": getattr(self.scope.get("user"), "username", ""),
                            "origin": self.channel_name,
                        },
                    },
                )
            return

        msg = (content or {}).get("message", "").strip()
        if not msg:
            return
        try:
            now = time.time()
            self._rate_ts = [t for t in self._rate_ts if now - t < 5.0]
            if len(self._rate_ts) >= 5:
                await self.send_json(
                    {"type": "system.notice", "message": "You are sending messages too quickly"}
                )
                return
            self._rate_ts.append(now)
        except Exception:
            pass
        # Enforce mute/ban and slow-mode for group/dm
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            if uid:
                # Check mute/ban
                from django.utils import timezone

                mem = await _get_membership(self.room.id, uid)
                if mem is not None:
                    if getattr(mem, "banned", False):
                        await self.send_json(
                            {"type": "system.notice", "message": "You are banned in this room"}
                        )
                        return
                    mu = getattr(mem, "muted_until", None)
                    if mu and mu > timezone.now():
                        await self.send_json({"type": "system.notice", "message": "You are muted"})
                        return
                # Slow-mode
                ssecs = await _get_room_slow_mode(self.room.id)
                self.room.slow_mode_seconds = ssecs
                if ssecs:
                    key = (self.room.id, uid)
                    last = _last_sent.get(key, 0.0)
                    if now - last < float(ssecs):
                        await self.send_json(
                            {"type": "system.notice", "message": "Slow mode active"}
                        )
                        return
                    _last_sent[key] = now
        except Exception:
            pass
        # Per-member delay for group/dm
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            mem = await _get_membership(self.room.id, uid) if uid else None
            if mem is not None:
                dsecs = int(getattr(mem, "delay_seconds", 0) or 0)
                if dsecs > 0:
                    await _create_delayed_message(self.room.id, uid, msg, None, dsecs)
                    await self.send_json(
                        {
                            "type": "system.notice",
                            "message": f"Your message will be delivered in {dsecs}s",
                        }
                    )
                    # Flush due items after enqueuing
                    due = await _fetch_and_publish_due(self.room.id)
                    for p in due:
                        await self.channel_layer.group_send(
                            self.room_name, {"type": "chat_message", "payload": p}
                        )
                    return
        except Exception:
            pass
        m = await _persist_room_message(self.room.id, self.scope.get("user"), msg)
        try:
            await _mark_published(m.id)
        except Exception:
            pass
        # Create in-app notifications (best-effort)
        try:
            await _notify_message(m.id)
        except Exception:
            pass
        created_dt = getattr(m, "created_at", None)
        payload = {
            "type": "message.new",
            "id": getattr(m, "id", None),
            "sender": getattr(self.scope.get("user"), "username", ""),
            "message": msg,
            "created_at": created_dt.isoformat() if created_dt else None,
            "parent_id": None,
        }
        await self.channel_layer.group_send(
            self.room_name, {"type": "chat_message", "payload": payload}
        )
        try:
            due = await _fetch_and_publish_due(self.room.id)
            for p in due:
                await self.channel_layer.group_send(
                    self.room_name, {"type": "chat_message", "payload": p}
                )
        except Exception:
            pass

    async def chat_message(self, event):
        payload = event.get("payload", {})
        if payload.get("origin") == self.channel_name and str(payload.get("type", "")).startswith(
            "typing"
        ):
            return
        if payload.get("origin") == self.channel_name and payload.get("type") == "presence.state":
            return
        await self.send_json(payload)

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        except Exception:
            pass
        # Presence leave
        try:
            uid = getattr(self.scope.get("user"), "id", None)
            if uid and self.room and self.room.id in _presence and uid in _presence[self.room.id]:
                _presence[self.room.id].remove(uid)
                if len(_presence[self.room.id]) > 0:
                    try:
                        users = await _usernames_for_ids(list(_presence[self.room.id]))
                    except Exception:
                        users = []
                    await self.channel_layer.group_send(
                        self.room_name,
                        {
                            "type": "chat_message",
                            "payload": {
                                "type": "presence.state",
                                "count": len(_presence[self.room.id]),
                                "users": users,
                                "origin": self.channel_name,
                            },
                        },
                    )
        except Exception:
            pass


@database_sync_to_async
def _get_membership(room_id: int, user_id: int):
    try:
        return RoomMembership.objects.get(room_id=room_id, user_id=user_id)
    except RoomMembership.DoesNotExist:
        return None


@database_sync_to_async
def _usernames_for_ids(ids: list[int]) -> list[str]:
    try:
        return list(User.objects.filter(id__in=ids).values_list("username", flat=True))
    except Exception:
        return []


@database_sync_to_async
def _get_room_slow_mode(room_id: int) -> int:
    try:
        from django.utils import timezone as _tz

        from .models import Room  # local import to avoid cycles

        r = Room.objects.only("slow_mode_seconds", "slow_mode_expires_at").get(pk=room_id)
        secs = int(r.slow_mode_seconds or 0)
        if secs and r.slow_mode_expires_at and _tz.now() >= r.slow_mode_expires_at:
            r.slow_mode_seconds = 0
            r.slow_mode_expires_at = None
            r.save(update_fields=["slow_mode_seconds", "slow_mode_expires_at"])
            return 0
        return secs
    except Exception:
        return 0


@database_sync_to_async
def _create_delayed_message(
    room_id: int, user_id: int, text: str, parent_id: int | None, delay_secs: int
) -> int:
    from .models import Message

    if len(text) > 500:
        text = text[:500]
    vis = timezone.now() + timedelta(seconds=max(1, int(delay_secs)))
    m = Message.objects.create(
        room_id=room_id, sender_id=user_id, text=text, parent_message_id=parent_id, visible_at=vis
    )
    return m.id


@database_sync_to_async
def _fetch_and_publish_due(room_id: int, limit: int = 20) -> list[dict]:
    from .models import Message

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
            # Create in-app notifications for matured messages
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


@database_sync_to_async
def _mark_published(message_id: int) -> None:
    from .models import Message

    Message.objects.filter(id=message_id, published_at__isnull=True).update(
        published_at=timezone.now()
    )


@database_sync_to_async
def _notify_message(message_id: int) -> int:
    try:
        return notify_message_by_id(message_id)
    except Exception:
        return 0


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser):
            await self.close(code=4001)
            return
        self.user_id = getattr(user, "id", None)
        if not self.user_id:
            await self.close(code=4001)
            return
        self.group = f"user_{self.user_id}_notifications"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def receive_json(self, content, **kwargs):  # no-op
        return

    async def notif_message(self, event):
        payload = event.get("payload", {})
        await self.send_json(payload)

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.group, self.channel_name)
        except Exception:
            pass
