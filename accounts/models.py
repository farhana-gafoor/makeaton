"""
accounts/models.py
==================
Purpose:
    Defines the custom User model for the BrightLoop project.
    Uses email as the unique login identifier and supports role-based access control
    with three distinct roles: Admin, Staff, and Customer.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom manager for User model where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        Defaults role to 'customer' unless explicitly specified.
        """
        if not email:
            raise ValueError(_("The Email field must be set"))

        email = self.normalize_email(email).lower()
        extra_fields.setdefault("role", User.ROLE_CUSTOMER)

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a Superuser with the given email and password.
        Ensures is_staff=True, is_superuser=True, and role='admin'.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.ROLE_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for BrightLoop.
    
    Fields:
        - email: unique, used for authentication
        - role: 'admin', 'staff', or 'customer'
        - first_name, last_name: inherited from AbstractUser
        - is_active, is_staff, is_superuser: standard Django permission flags
    """

    # Role constants for type-safety and consistency across apps
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"
    ROLE_CUSTOMER = "customer"

    ROLE_CHOICES = (
        (ROLE_ADMIN, _("Admin (Full System Access)")),
        (ROLE_STAFF, _("Staff (Operations & Support)")),
        (ROLE_CUSTOMER, _("Customer (Self-service subscriber)")),
    )

    # Disable the default username field so email is the sole credential
    username = None

    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        error_messages={
            "unique": _("A user with this email address already exists."),
        },
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
        help_text=_("Designates the user's privilege tier across the application."),
    )

    # Inform Django that email is the primary login field
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No extra prompt fields when running 'createsuperuser'

    objects = CustomUserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.email}) [{self.role}]"
        return f"{self.email} [{self.role}]"

    # Convenient helper properties for checking roles in templates and Python code
    @property
    def is_role_admin(self) -> bool:
        """True if user has the 'admin' role or is a Django superuser."""
        return self.is_superuser or self.role == self.ROLE_ADMIN

    @property
    def is_role_staff(self) -> bool:
        """True if user has the 'staff' role or 'admin' role."""
        return self.is_superuser or self.role in [self.ROLE_ADMIN, self.ROLE_STAFF]

    @property
    def is_role_customer(self) -> bool:
        """True if user has the 'customer' role."""
        return self.role == self.ROLE_CUSTOMER
