from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

from courses.models import Course
from courses.views import course_list


@pytest.mark.django_db
def test_courses_list_query_budget(django_assert_num_queries):
    owner = User.objects.create_user(username="ownqb", password="pw")
    for i in range(5):
        Course.objects.create(owner=owner, title=f"Q{i}")
    rf = RequestFactory()
    req = rf.get("/courses/")
    req.user = AnonymousUser()
    # Anonymous list should perform a small number of queries (at most 10)
    with django_assert_num_queries(10, exact=False):
        resp = course_list(req)
        assert resp.status_code == 200
