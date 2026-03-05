from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from courses.models import Enrolment


@pytest.mark.django_db
def test_add_student_search_results_render(client, teacher_user, make_course):
    course = make_course(owner=teacher_user, title="Roster Course")
    # Create a few students
    s1 = User.objects.create_user(username="amy", password="pw")
    s1.profile.role = "student"
    s1.profile.save(update_fields=["role"])
    s2 = User.objects.create_user(username="amber", password="pw")
    s2.profile.role = "student"
    s2.profile.save(update_fields=["role"])

    client.force_login(teacher_user)
    url = reverse("courses:add-student", args=[course.pk])
    r = client.post(url, data={"action": "search", "query": "am"})
    assert r.status_code == 200
    # Should render both matching usernames
    content = r.content.decode()
    assert "amy" in content and "amber" in content


@pytest.mark.django_db
def test_add_student_enrol_and_already_enrolled_message(client, teacher_user, make_course):
    course = make_course(owner=teacher_user, title="Roster Course 2")
    stu = User.objects.create_user(username="bob", password="pw")
    stu.profile.role = "student"
    stu.profile.save(update_fields=["role"])

    client.force_login(teacher_user)
    url = reverse("courses:add-student", args=[course.pk])
    # First enrol succeeds
    r1 = client.post(url, data={"query": "bob"})
    assert r1.status_code == 302
    assert Enrolment.objects.filter(course=course, student=stu).count() == 1
    # Second attempt should not duplicate
    r2 = client.post(url, data={"query": "bob"})
    assert r2.status_code == 302
    assert Enrolment.objects.filter(course=course, student=stu).count() == 1


@pytest.mark.django_db
def test_remove_student_post(client, teacher_user, make_course, student_user):
    course = make_course(owner=teacher_user, title="Roster Course 3")
    Enrolment.objects.create(course=course, student=student_user)
    client.force_login(teacher_user)
    url = reverse("courses:remove", args=[course.pk, student_user.pk])
    r = client.post(url)
    assert r.status_code == 302
    assert not Enrolment.objects.filter(course=course, student=student_user).exists()
