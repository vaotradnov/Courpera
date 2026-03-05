from __future__ import annotations

import importlib

import pytest
from django.test import RequestFactory, override_settings


@pytest.mark.django_db
def test_catalogue_cache_toggle_via_reload(settings):
    rf = RequestFactory()

    with override_settings(CATALOGUE_CACHE_ENABLED=True, CATALOGUE_CACHE_SECONDS=60):
        views = importlib.import_module("courses.views")
        importlib.reload(views)
        req = rf.get("/courses/")
        # Anonymous user
        from django.contrib.auth.models import AnonymousUser

        req.user = AnonymousUser()
        resp = views.course_list(req)
        assert resp.status_code == 200
        cc = resp.headers.get("Cache-Control", "").lower()
        assert "max-age" in cc

    with override_settings(CATALOGUE_CACHE_ENABLED=False):
        views = importlib.import_module("courses.views")
        importlib.reload(views)
        req = rf.get("/courses/")
        from django.contrib.auth.models import AnonymousUser

        req.user = AnonymousUser()
        resp = views.course_list(req)
        assert resp.status_code == 200
        cc = resp.headers.get("Cache-Control", "").lower()
        assert "max-age" not in cc
