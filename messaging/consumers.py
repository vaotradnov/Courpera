from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from courses.models import Course, Enrolment

from .models import ChatMessage


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
def _persist_message(room: str, course: Course | None, sender, text: str):
    if len(text) > 500:
        text = text[:500]
    ChatMessage.objects.create(room=room, course=course, sender=sender, text=text)


class CourseChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.course_id = int(self.scope["url_route"]["kwargs"]["course_id"])
        ok, reason, course = await _course_auth(self.scope.get("user"), self.course_id)
        if not ok:
            await self.close(code=4001)
            return
        self.course = course
        self.room_name = f"course_{self.course_id}"
        # Simple per-connection rate limiter: max 5 messages per 5 seconds
        self._rate_ts = []
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def receive_json(self, content, **kwargs):
        msg = (content or {}).get("message", "").strip()
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
        await _persist_message(self.room_name, self.course, self.scope.get("user"), msg)
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
