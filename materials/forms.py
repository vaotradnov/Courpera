"""Forms for uploading course materials."""

from __future__ import annotations

from django import forms

from .models import Material, validate_upload


class MaterialUploadForm(forms.ModelForm):
    """Teacher-facing upload form (25 MB cap, PDF/JPEG/PNG/WEBP)."""

    class Meta:
        model = Material
        fields = ("title", "file")

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            validate_upload(f)
        return f
