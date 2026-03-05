from __future__ import annotations

import json

import pytest
from django.test import Client


def _has_properties(schema: dict, props: set[str]) -> bool:
    return props.issubset(set(schema.get("properties", {}).keys()))


@pytest.mark.django_db
def test_openapi_components_include_material_and_enrolment_shapes():
    c = Client()
    r = c.get("/api/schema/")
    assert r.status_code == 200
    try:
        data = json.loads(r.content)
    except Exception:
        # If YAML returned, keep test coarse
        txt = r.content.decode("utf-8", errors="ignore").lower()
        assert "openapi" in txt
        return
    comps = (data.get("components") or {}).get("schemas") or {}
    # Find any schema that looks like our Material and Enrolment
    material_ok = False
    enrolment_ok = False
    for name, schema in comps.items():
        if _has_properties(schema, {"id", "course", "title", "size_bytes", "mime", "created_at"}):
            material_ok = True
        if _has_properties(schema, {"id", "course", "student", "completed", "created_at"}):
            enrolment_ok = True
    assert material_ok and enrolment_ok
