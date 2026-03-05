"""Materials models and validators (Stage 6: uploads).

Defines `Material` uploaded by a teacher to a course. Uploads are
limited to 25 MB and a small set of MIME types / extensions to keep the
demo safe and predictable.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from courses.models import Course

ALLOWED_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 25 * 1024 * 1024


def validate_upload(file) -> None:
    """Validate file size and a conservative type check.

    Notes:
    - Use uploaded file size and extension; we also attempt to guess
      MIME from the filename for an additional hint.
    - This avoids extra dependencies (no libmagic) while still being
      sufficiently restrictive for coursework demonstration.
    """
    size = getattr(file, "size", None)
    if size is not None and size > MAX_BYTES:
        raise ValidationError("File too large (max 25 MB)")
    ext = Path(getattr(file, "name", "")).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValidationError("Unsupported file type")
    guessed, _ = mimetypes.guess_type(getattr(file, "name", ""))
    if guessed and guessed not in ALLOWED_MIME:
        raise ValidationError("Unsupported MIME type")


class Material(models.Model):
    """A file attached to a course, uploaded by a teacher."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="materials/", validators=[validate_upload])
    size_bytes = models.PositiveIntegerField(default=0)
    mime = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Derive size and MIME on save for display and quick checks.
        f = self.file
        try:
            self.size_bytes = getattr(f, "size", self.size_bytes) or 0
            self.mime = mimetypes.guess_type(getattr(f, "name", ""))[0] or ""
        except Exception:
            pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.title} ({self.course_id})"
