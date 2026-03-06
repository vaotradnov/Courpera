from __future__ import annotations

from django.urls import path

from .consumers import CourseChatConsumer, RoomConsumer

websocket_urlpatterns = [
    path("ws/chat/course/<int:course_id>/", CourseChatConsumer.as_asgi()),
    path("ws/chat/room/<int:room_id>/", RoomConsumer.as_asgi()),
]
