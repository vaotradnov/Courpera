"""Messaging models for persisted chat messages."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from courses.models import Course


class ChatMessage(models.Model):
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
