"""Messaging models for persisted chat messages (v2 rooms + legacy)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from courses.models import Course


class ChatMessage(models.Model):
    """
    Legacy message model used by the initial course chat implementation.
    Kept for migration/backwards-compat but no longer written in new code.
    """

    room = models.CharField(max_length=100, db_index=True)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True, related_name="chat_messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages"
    )
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.room}:{self.sender_id}:{self.text[:16]}"


class Room(models.Model):
    KIND_COURSE = "course"
    KIND_DM = "dm"
    KIND_GROUP = "group"
    KIND_CHOICES = (
        (KIND_COURSE, "Course"),
        (KIND_DM, "Direct"),
        (KIND_GROUP, "Group"),
    )

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True, related_name="rooms"
    )
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["kind", "created_at"], name="msg_room_kind_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        base = self.kind
        if self.kind == self.KIND_COURSE and self.course_id:
            base += f"#{self.course_id}"
        elif self.title:
            base += f":{self.title[:12]}"
        return base


class RoomMembership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"
    ROLE_CHOICES = ((ROLE_OWNER, "Owner"), (ROLE_MEMBER, "Member"))

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="room_memberships"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("room", "user")
        indexes = [
            models.Index(fields=["user", "created_at"], name="msg_mem_user_created_idx"),
        ]


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["room", "created_at"], name="msg_room_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"r{self.room_id}:{self.sender_id}:{self.text[:16]}"
