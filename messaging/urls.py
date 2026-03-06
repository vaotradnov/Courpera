from django.urls import path

from .views import (
    course_history,
    create_dm,
    create_group,
    delete_message,
    edit_message,
    room_messages,
    toggle_reaction,
)

app_name = "messaging"

urlpatterns = [
    path("course/<int:course_id>/history/", course_history, name="course-history"),
    path("rooms/<int:room_id>/messages/", room_messages, name="room-messages"),
    path("rooms/dm/", create_dm, name="create-dm"),
    path("rooms/group/", create_group, name="create-group"),
    path("messages/<int:message_id>/", edit_message, name="edit-message"),
    path("messages/<int:message_id>/delete/", delete_message, name="delete-message"),
    path("messages/<int:message_id>/reactions/", toggle_reaction, name="toggle-reaction"),
]
