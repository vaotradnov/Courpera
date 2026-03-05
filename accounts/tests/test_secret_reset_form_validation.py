from __future__ import annotations

from accounts.forms import SecretResetForm


def test_secret_reset_form_password_mismatch_validation():
    form = SecretResetForm(
        data={
            "identifier": "user@example.com",
            "secret_word": "secretword",
            "new_password1": "Abcdef123$",
            "new_password2": "Different123$",
        }
    )
    assert form.is_valid() is False
    assert "Passwords do not match." in str(form.errors)
