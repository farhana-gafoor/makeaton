"""
subscriptions/tests.py
======================
Purpose:
    Unit tests for Subscription status transitions and finite state machine.
"""

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from catalog.models import Plan
from subscriptions.models import Subscription

User = get_user_model()


class SubscriptionStateMachineTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="subtest@example.com", password="Password@123")
        self.plan = Plan.objects.create(name="Test Plan", price=Decimal("10.00"), billing_period=Plan.PERIOD_MONTHLY)
        self.sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            status=Subscription.STATUS_DRAFT,
        )

    def test_valid_transitions(self):
        # Draft -> Quotation is allowed
        self.sub.change_status(Subscription.STATUS_QUOTATION)
        self.assertEqual(self.sub.status, Subscription.STATUS_QUOTATION)

        # Quotation -> Confirmed is allowed
        self.sub.change_status(Subscription.STATUS_CONFIRMED)
        self.assertEqual(self.sub.status, Subscription.STATUS_CONFIRMED)

        # Confirmed -> Active is allowed
        self.sub.change_status(Subscription.STATUS_ACTIVE)
        self.assertEqual(self.sub.status, Subscription.STATUS_ACTIVE)

        # Active -> Closed is allowed
        self.sub.change_status(Subscription.STATUS_CLOSED)
        self.assertEqual(self.sub.status, Subscription.STATUS_CLOSED)

    def test_invalid_transitions(self):
        # Draft cannot jump directly to Active
        with self.assertRaises(ValidationError):
            self.sub.change_status(Subscription.STATUS_ACTIVE)

        # Closed cannot transition anywhere (terminal state)
        self.sub.status = Subscription.STATUS_CLOSED
        self.sub.save()
        with self.assertRaises(ValidationError):
            self.sub.change_status(Subscription.STATUS_DRAFT)
