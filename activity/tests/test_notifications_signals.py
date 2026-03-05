from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from activity.models import Notification
from courses.models import Course, Enrolment
from materials.models import Material


@pytest.mark.django_db
def test_enrolment_creates_notification_for_teacher():
    t = User.objects.create_user(username="t", password="pw")
    s = User.objects.create_user(username="s", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    s.profile.role = "student"
    s.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C", description="")
    assert Notification.objects.filter(user=t).count() == 0
    Enrolment.objects.create(course=c, student=s)
    assert (
        Notification.objects.filter(user=t, course=c, type=Notification.TYPE_ENROLMENT).count() == 1
    )


@pytest.mark.django_db
def test_material_upload_creates_notifications_for_enrolled_students():
    t = User.objects.create_user(username="t2", password="pw")
    s1 = User.objects.create_user(username="s1", password="pw")
    s2 = User.objects.create_user(username="s2", password="pw")
    for u, role in ((t, "teacher"), (s1, "student"), (s2, "student")):
        u.profile.role = role
        u.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C2", description="")
    Enrolment.objects.create(course=c, student=s1)
    Enrolment.objects.create(course=c, student=s2)
    f = SimpleUploadedFile("doc.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    m = Material.objects.create(course=c, uploaded_by=t, title="Doc", file=f)
    # Two notifications (one per enrolled student)
    assert Notification.objects.filter(course=c, type=Notification.TYPE_MATERIAL).count() == 2
