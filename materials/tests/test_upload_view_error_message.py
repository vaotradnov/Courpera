from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from courses.models import Course


@pytest.mark.django_db
def test_upload_view_shows_error_message_for_invalid_filetype(client):
    t = User.objects.create_user(username="t_err", password="pw")
    t.profile.role = "teacher"
    t.profile.save(update_fields=["role"])
    c = Course.objects.create(owner=t, title="C", description="")
    assert client.login(username="t_err", password="pw")
    # Bad extension triggers form error in the view path
    bad = SimpleUploadedFile("doc.exe", b"dummy", content_type="application/octet-stream")
    url = reverse("materials:upload", args=[c.pk])
    r = client.post(url, data={"title": "Doc", "file": bad}, follow=True)
    assert r.status_code == 200
    content = r.content.decode()
    assert "Unsupported file type" in content or "Upload failed" in content
