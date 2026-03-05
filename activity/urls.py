from django.urls import path

from .views import (
    notifications_mark_all_read,
    notifications_page,
    notifications_recent,
    post_status,
)

app_name = "activity"

urlpatterns = [
    path("status/", post_status, name="post-status"),
    path("notifications/recent/", notifications_recent, name="notifications-recent"),
    path("notifications/", notifications_page, name="notifications-page"),
    path(
        "notifications/mark-all-read/",
        notifications_mark_all_read,
        name="notifications-mark-all-read",
    ),
]
