from __future__ import annotations

from django.urls import re_path

from .consumers import CourseChatConsumer, RoomConsumer

websocket_urlpatterns = [
    re_path(r"^ws/chat/course/(?P<course_id>\d+)/$", CourseChatConsumer.as_asgi()),
    re_path(r"^ws/chat/room/(?P<room_id>\d+)/$", RoomConsumer.as_asgi()),
]
