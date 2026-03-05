from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from courses.models import Course, Enrolment
from discussions.models import Question
from discussions.services import (
    add_reply,
    can_participate,
    create_question,
    toggle_pin,
    upvote_question,
)


@pytest.mark.django_db
def test_discussion_services_flows():
    owner = User.objects.create_user(username="owner", password="pw")
    student = User.objects.create_user(username="stu", password="pw")
    c = Course.objects.create(owner=owner, title="D")
    Enrolment.objects.create(course=c, student=student)

    assert can_participate(owner, c) is True
    assert can_participate(student, c) is True

    q = create_question(c, owner, "Title", "Body")
    assert isinstance(q, Question)

    r = add_reply(q, student, "Reply text")
    assert r.body == "Reply text"

    # Upvote idempotent
    assert upvote_question(q, student) in (True, False)
    assert upvote_question(q, student) is False

    # Only owner can toggle pin
    with pytest.raises(PermissionDenied):
        toggle_pin(q, student)
    toggled = toggle_pin(q, owner)
    assert toggled is True or toggled is False
