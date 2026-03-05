from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory

from accounts.decorators import role_required


def test_role_required_unauthenticated_raises_permission_denied() -> None:
    rf = RequestFactory()
    req = rf.get("/")

    @role_required("teacher")
    def view(request):  # pragma: no cover - never reached
        return None

    with pytest.raises(PermissionDenied):
        view(req)
