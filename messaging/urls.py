from django.urls import path

from .views import course_history

app_name = "messaging"

urlpatterns = [
    path("course/<int:course_id>/history/", course_history, name="course-history"),
]
