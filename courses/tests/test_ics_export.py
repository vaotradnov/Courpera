from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from courses.models import Course
from materials.models import Material


@pytest.mark.django_db
def test_course_calendar_ics_contains_events():
    t = User.objects.create_user(username="tics", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="ICS Course", description="")
    f1 = SimpleUploadedFile("intro.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    f2 = SimpleUploadedFile("w1.pdf", b"%PDF-1.4\n", content_type="application/pdf")
    Material.objects.create(course=c, uploaded_by=t, title="Intro", file=f1)
    Material.objects.create(course=c, uploaded_by=t, title="Week 1", file=f2)

    client = Client()
    r = client.get(f"/courses/{c.pk}/calendar.ics")
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/calendar")
    cd = r.headers.get("Content-Disposition", "")
    assert f"course-{c.pk}.ics" in cd
    body = r.content.decode("utf-8", errors="ignore")
    assert "BEGIN:VCALENDAR" in body and "END:VCALENDAR" in body
    assert "PRODID:-//Courpera//Course Calendar//EN" in body
    # Expect at least one VEVENT with course + material title in summary
    assert "BEGIN:VEVENT" in body
    assert "SUMMARY:ICS Course: Intro" in body or "SUMMARY:ICS Course: Week 1" in body
