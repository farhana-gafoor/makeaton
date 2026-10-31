"""
accounts/tests.py
=================
Purpose:
    Unit tests for the custom User model, password validator, role decorators,
    and the filter_by_user data-scoping utility.
"""

from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from accounts.validators import CustomComplexityValidator
from accounts.decorators import role_required
from accounts.utils import filter_by_user

User = get_user_model()


class CustomPasswordValidatorTests(TestCase):
    def setUp(self):
        self.validator = CustomComplexityValidator()

    def test_valid_password(self):
        # >8 chars, has upper, lower, special
        self.validator.validate("Valid@1234")

    def test_too_short_password(self):
        # Exactly 8 chars must fail (rule: > 8 chars)
        with self.assertRaises(ValidationError):
            self.validator.validate("Short@1A")

    def test_missing_uppercase(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("lowercase@123")

    def test_missing_lowercase(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("UPPERCASE@123")

    def test_missing_special_character(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("NoSpecialChar123")


class UserModelTests(TestCase):
    def test_create_customer(self):
        user = User.objects.create_user(email="test@customer.local", password="Password@123")
        self.assertEqual(user.role, User.ROLE_CUSTOMER)
        self.assertTrue(user.is_role_customer)
        self.assertFalse(user.is_role_staff)
        self.assertFalse(user.is_role_admin)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@system.local", password="Password@123")
        self.assertEqual(admin.role, User.ROLE_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_role_admin)


class ScopingHelperTests(TestCase):
    def test_filter_by_user_anonymous(self):
        anon = AnonymousUser()
        qs = filter_by_user(User.objects.all(), anon, user_field="id")
        self.assertEqual(qs.count(), 0)

    def test_filter_by_user_customer(self):
        from subscriptions.models import Subscription
        from catalog.models import Plan

        user1 = User.objects.create_user(email="c1@test.com", password="Password@123")
        user2 = User.objects.create_user(email="c2@test.com", password="Password@123")
        plan = Plan.objects.create(name="Basic", price=10, billing_period="monthly")

        sub1 = Subscription.objects.create(customer=user1, plan=plan)
        sub2 = Subscription.objects.create(customer=user2, plan=plan)

        # When user1 queries, only user1's records returned
        qs = filter_by_user(Subscription.objects.all(), user1, user_field="customer")
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().customer, user1)
