from __future__ import annotations

from django.urls import re_path

from .consumers import CourseChatConsumer

websocket_urlpatterns = [
    re_path(r"^ws/chat/course/(?P<course_id>\d+)/$", CourseChatConsumer.as_asgi()),
]
