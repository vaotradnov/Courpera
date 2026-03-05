from django.urls import path

from .views import (
    CourperaLoginView,
    CourperaLogoutView,
    CourperaPasswordChangeView,
    avatar_proxy,
    home,
    home_student,
    home_teacher,
    password_change_done,
    password_forgot,
    profile_edit,
    register,
    search_users,
    student_grades,
)

app_name = "accounts"

urlpatterns = [
    path("login/", CourperaLoginView.as_view(), name="login"),
    path("logout/", CourperaLogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("password/change/", CourperaPasswordChangeView.as_view(), name="password-change"),
    path("password/change/done/", password_change_done, name="password-change-done"),
    path("password/forgot/", password_forgot, name="password-forgot"),
    path("home/", home, name="home"),
    path("home/teacher/", home_teacher, name="home-teacher"),
    path("home/student/", home_student, name="home-student"),
    path("profile/", profile_edit, name="profile"),
    path("search/", search_users, name="search"),
    path("avatar/<int:user_id>/<int:size>/", avatar_proxy, name="avatar-proxy"),
    path("grades/", student_grades, name="grades"),
]
