"""
billing/tests.py
================
Purpose:
    Unit tests for Invoice unique constraints, status transitions, dynamic properties,
    and Payment validation.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from catalog.models import Plan
from subscriptions.models import Subscription
from billing.models import Invoice, Payment

User = get_user_model()


class BillingModelTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email="billingtest@example.com", password="Password@123")
        self.plan = Plan.objects.create(name="Pro Plan", price=Decimal("100.00"), billing_period=Plan.PERIOD_MONTHLY)
        self.sub = Subscription.objects.create(customer=self.customer, plan=self.plan, status=Subscription.STATUS_ACTIVE)
        self.today = date.today()

    def test_unique_period_start_constraint(self):
        # First invoice for this period
        Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        # Duplicate invoice for the same subscription and period_start MUST fail
        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                subscription=self.sub,
                period_start=self.today,
                period_end=self.today + timedelta(days=30),
                total=Decimal("100.00"),
                due_date=self.today + timedelta(days=14),
            )

    def test_payment_amount_validation(self):
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today - timedelta(days=40),
            period_end=self.today - timedelta(days=10),
            total=Decimal("100.00"),
            due_date=self.today,
        )

        # Payment <= 0 must fail
        with self.assertRaises(ValidationError):
            p_zero = Payment(invoice=inv, amount=Decimal("0.00"), method=Payment.METHOD_CREDIT_CARD)
            p_zero.clean()

        # Payment exceeding balance (e.g. 150 on a 100 balance) must fail
        with self.assertRaises(ValidationError):
            p_excess = Payment(invoice=inv, amount=Decimal("150.00"), method=Payment.METHOD_CREDIT_CARD)
            p_excess.clean()

        # Valid payment succeeds
        p_valid = Payment.objects.create(invoice=inv, amount=Decimal("60.00"), method=Payment.METHOD_CREDIT_CARD)
        self.assertEqual(inv.balance_due, Decimal("40.00"))
        self.assertEqual(inv.amount_paid, Decimal("60.00"))
