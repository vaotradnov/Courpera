from django.urls import path

from .views import (
    course_add_student,
    course_create,
    course_detail,
    course_edit,
    course_enrol,
    course_feedback,
    course_gradebook,
    course_gradebook_csv,
    course_list,
    course_remove_student,
    course_syllabus_edit,
    course_unenrol,
)
from .views_ics import course_calendar

app_name = "courses"

urlpatterns = [
    path("", course_list, name="list"),
    path("create/", course_create, name="create"),
    path("<int:pk>/", course_detail, name="detail"),
    path("<int:pk>/edit/", course_edit, name="edit"),
    path("<int:pk>/syllabus/edit/", course_syllabus_edit, name="syllabus-edit"),
    path("<int:pk>/enrol/", course_enrol, name="enrol"),
    path("<int:pk>/unenrol/", course_unenrol, name="unenrol"),
    path("<int:pk>/feedback/", course_feedback, name="feedback"),
    path("<int:pk>/calendar.ics", course_calendar, name="calendar"),
    path("<int:pk>/remove/<int:user_id>/", course_remove_student, name="remove"),
    path("<int:pk>/add-student/", course_add_student, name="add-student"),
    path("<int:pk>/gradebook/", course_gradebook, name="gradebook"),
    path("<int:pk>/gradebook.csv", course_gradebook_csv, name="gradebook-csv"),
]
