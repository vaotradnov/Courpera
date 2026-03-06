from django.urls import path

from .views import course_history, create_dm, create_group, room_messages

app_name = "messaging"

urlpatterns = [
    path("course/<int:course_id>/history/", course_history, name="course-history"),
    path("rooms/<int:room_id>/messages/", room_messages, name="room-messages"),
    path("rooms/dm/", create_dm, name="create-dm"),
    path("rooms/group/", create_group, name="create-group"),
]
