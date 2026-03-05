from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    """Require a mix of character classes for stronger passwords.

    Rules (in addition to minimum length configured separately):
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one symbol (non-alphanumeric)
    """

    uppercase = re.compile(r"[A-Z]")
    lowercase = re.compile(r"[a-z]")
    digit = re.compile(r"\d")
    symbol = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password: str, user=None):  # noqa: D401
        if not self.uppercase.search(password):
            raise ValidationError(_("Password must contain an uppercase letter."))
        if not self.lowercase.search(password):
            raise ValidationError(_("Password must contain a lowercase letter."))
        if not self.digit.search(password):
            raise ValidationError(_("Password must contain a digit."))
        if not self.symbol.search(password):
            raise ValidationError(_("Password must contain a symbol."))

    def get_help_text(self):  # noqa: D401
        return _("Password must include uppercase, lowercase, digit, and symbol.")
