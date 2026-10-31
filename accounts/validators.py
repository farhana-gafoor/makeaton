"""
accounts/validators.py
======================
Purpose:
    Custom password complexity validation for BrightLoop users.
    Enforces security standards across customer, staff, and admin accounts.

Rules enforced:
    - Must be strictly MORE than 8 characters (> 8)
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one special character (e.g. !@#$%^&*...)
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomComplexityValidator:
    """
    Validates that a password satisfies the project's security criteria:
    - Length > 8
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """

    def validate(self, password, user=None):
        # 1. More than 8 characters
        if len(password) <= 8:
            raise ValidationError(
                _("Password must be more than 8 characters long (minimum 9 characters)."),
                code="password_too_short",
            )

        # 2. At least one uppercase letter
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter (A-Z)."),
                code="password_no_upper",
            )

        # 3. At least one lowercase letter
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter (a-z)."),
                code="password_no_lower",
            )

        # 4. At least one special character
        # Matches any non-alphanumeric character
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g., !@#$%^&*)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Your password must be more than 8 characters long and include at least "
            "one uppercase letter, one lowercase letter, and one special character."
        )
