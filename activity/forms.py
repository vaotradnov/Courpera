"""Forms for status updates."""

from __future__ import annotations

from django import forms

from .models import Status


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ("text",)
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 2, "maxlength": 280, "placeholder": "Share an update..."}
            ),
        }
