from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from courses.models import Course, Enrolment

from .models import Message, Room, RoomMembership


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
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def receive_json(self, content, **kwargs):
        msg = (content or {}).get("message", "").strip()
        parent_id = content.get("parent_id") if isinstance(content, dict) else None
        if not msg:
            return
        # Enforce basic per-connection rate limiting to reduce spam
        try:
            import time

            now = time.time()
            self._rate_ts = [t for t in self._rate_ts if now - t < 5.0]
            if len(self._rate_ts) >= 5:
                # Drop message silently to avoid feedback loops
                return
            self._rate_ts.append(now)
        except Exception:
            pass
        m = await _persist_room_message(
            self.room.id,
            self.scope.get("user"),
            msg,
            parent_id if isinstance(parent_id, int) else None,
        )
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

    async def chat_message(self, event):
        await self.send_json(event["payload"])

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
    ok = RoomMembership.objects.filter(room=room, user=user).exists()
    return (ok, "Join this room to participate" if not ok else "", room)


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
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def receive_json(self, content, **kwargs):
        msg = (content or {}).get("message", "").strip()
        if not msg:
            return
        try:
            import time

            now = time.time()
            self._rate_ts = [t for t in self._rate_ts if now - t < 5.0]
            if len(self._rate_ts) >= 5:
                return
            self._rate_ts.append(now)
        except Exception:
            pass
        await _persist_room_message(self.room.id, self.scope.get("user"), msg)
        payload = {
            "type": "chat.message",
            "sender": getattr(self.scope.get("user"), "username", ""),
            "message": msg,
        }
        await self.channel_layer.group_send(
            self.room_name, {"type": "chat_message", "payload": payload}
        )

    async def chat_message(self, event):
        await self.send_json(event["payload"])

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        except Exception:
            pass
