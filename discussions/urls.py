from django.urls import path

from .views import course_qna

app_name = "discussions"

urlpatterns = [
    path("course/<int:course_id>/", course_qna, name="course-qna"),
]
