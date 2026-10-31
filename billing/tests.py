"""
billing/tests.py
================
Purpose:
    Unit tests for billing models, validations, dynamic financial calculations,
    status transitions, and manager queries.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from catalog.models import Plan, Product
from subscriptions.models import Subscription
from billing.models import Discount, Invoice, InvoiceLine, Payment

User = get_user_model()


class BillingModelTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            email="staff_billing@example.local",
            password="Password@123",
            role=User.ROLE_STAFF,
        )
        self.customer = User.objects.create_user(
            email="billingtest@example.com",
            password="Password@123",
            role=User.ROLE_CUSTOMER,
        )
        self.plan = Plan.objects.create(
            name="Pro Monthly",
            price=Decimal("100.00"),
            billing_period=Plan.PERIOD_MONTHLY,
        )
        self.product = Product.objects.create(
            name="Cloud Storage 100GB",
            sales_price=Decimal("50.00"),
        )
        self.sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        self.today = date.today()

    def test_unique_period_start_constraint(self):
        """Verifies duplicate invoice creation for the same subscription and period_start is blocked."""
        Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                subscription=self.sub,
                period_start=self.today,
                period_end=self.today + timedelta(days=30),
                total=Decimal("100.00"),
                due_date=self.today + timedelta(days=14),
            )

    def test_invoice_auto_number_and_properties(self):
        """Verifies invoice number auto-generation, subtotal, balance_due, and aliases."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            subtotal=Decimal("100.00"),
            discount_total=Decimal("10.00"),
            tax_total=Decimal("16.20"),
            total=Decimal("106.20"),
            due_date=self.today + timedelta(days=14),
        )

        self.assertTrue(inv.invoice_number.startswith("INV-"))
        self.assertEqual(inv.number, inv.invoice_number)
        self.assertEqual(inv.discount_amount, Decimal("10.00"))
        self.assertEqual(inv.tax_amount, Decimal("16.20"))
        self.assertEqual(inv.amount_paid, Decimal("0.00"))
        self.assertEqual(inv.balance_due, Decimal("106.20"))

    def test_invoice_line_computed_properties(self):
        """Verifies InvoiceLine computed properties: subtotal, tax, and total."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("118.00"),
            due_date=self.today + timedelta(days=14),
        )

        line = InvoiceLine.objects.create(
            invoice=inv,
            product=self.product,
            description="Cloud Storage",
            quantity=2,
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("18.00"),
        )

        self.assertEqual(line.line_subtotal, Decimal("100.00"))
        self.assertEqual(line.line_tax, Decimal("18.00"))
        self.assertEqual(line.line_total, Decimal("118.00"))
        self.assertEqual(line.amount, Decimal("100.00"))

    def test_payment_validation_zero_and_negative(self):
        """Verifies zero or negative payments are blocked by validation and save."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        # Zero payment
        with self.assertRaises(ValidationError):
            p_zero = Payment(invoice=inv, amount=Decimal("0.00"), method=Payment.METHOD_CARD)
            p_zero.clean()

        with self.assertRaises(ValidationError):
            p_zero = Payment(invoice=inv, amount=Decimal("0.00"), method=Payment.METHOD_CARD)
            p_zero.save()

        # Negative payment
        with self.assertRaises(ValidationError):
            p_neg = Payment(invoice=inv, amount=Decimal("-10.00"), method=Payment.METHOD_CARD)
            p_neg.clean()

        with self.assertRaises(ValidationError):
            p_neg = Payment(invoice=inv, amount=Decimal("-10.00"), method=Payment.METHOD_CARD)
            p_neg.save()

    def test_payment_validation_overpayment(self):
        """Verifies payments exceeding balance due are blocked."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        with self.assertRaises(ValidationError):
            p_excess = Payment(invoice=inv, amount=Decimal("150.00"), method=Payment.METHOD_CARD)
            p_excess.clean()

        with self.assertRaises(ValidationError):
            p_excess = Payment(invoice=inv, amount=Decimal("150.00"), method=Payment.METHOD_CARD)
            p_excess.save()

    def test_payment_editing_excludes_self_from_balance(self):
        """Verifies editing an existing payment correctly excludes itself when checking balance due."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        p1 = Payment.objects.create(
            invoice=inv,
            amount=Decimal("40.00"),
            method=Payment.METHOD_CARD,
            recorded_by=self.staff_user,
        )

        # Can increase amount up to the remaining total (100.00)
        p1.amount = Decimal("80.00")
        p1.clean()
        p1.save()

        self.assertEqual(inv.amount_paid, Decimal("80.00"))
        self.assertEqual(inv.balance_due, Decimal("20.00"))

        # Cannot exceed total
        p1.amount = Decimal("105.00")
        with self.assertRaises(ValidationError):
            p1.clean()

    def test_partial_payment_then_full_payment_marks_invoice_paid(self):
        """Verifies partial payment reduces balance, and full settlement marks CONFIRMED invoice as PAID."""
        inv = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=self.today + timedelta(days=30),
            status=Invoice.STATUS_CONFIRMED,
            total=Decimal("100.00"),
            due_date=self.today + timedelta(days=14),
        )

        # Partial payment 1: $40.00
        Payment.objects.create(invoice=inv, amount=Decimal("40.00"), method=Payment.METHOD_CARD)
        inv.refresh_from_db()
        self.assertEqual(inv.amount_paid, Decimal("40.00"))
        self.assertEqual(inv.balance_due, Decimal("60.00"))
        self.assertEqual(inv.status, Invoice.STATUS_CONFIRMED)

        # Partial payment 2: $60.00 (remaining balance)
        Payment.objects.create(invoice=inv, amount=Decimal("60.00"), method=Payment.METHOD_UPI)
        inv.refresh_from_db()
        self.assertEqual(inv.amount_paid, Decimal("100.00"))
        self.assertEqual(inv.balance_due, Decimal("0.00"))
        self.assertEqual(inv.status, Invoice.STATUS_PAID)

    def test_overdue_and_outstanding_queries(self):
        """Verifies overdue() and outstanding() manager querysets return expected invoices."""
        past_date = self.today - timedelta(days=20)
        future_date = self.today + timedelta(days=20)

        # 1. Overdue and confirmed (should be in both overdue and outstanding)
        inv_overdue = Invoice.objects.create(
            subscription=self.sub,
            period_start=past_date - timedelta(days=30),
            period_end=past_date,
            status=Invoice.STATUS_CONFIRMED,
            total=Decimal("100.00"),
            due_date=past_date,
        )

        # 2. Overdue but PAID (should NOT be in overdue or outstanding)
        inv_paid_past = Invoice.objects.create(
            subscription=self.sub,
            period_start=past_date - timedelta(days=60),
            period_end=past_date - timedelta(days=30),
            status=Invoice.STATUS_PAID,
            total=Decimal("100.00"),
            due_date=past_date,
        )
        Payment.objects.create(invoice=inv_paid_past, amount=Decimal("100.00"), method=Payment.METHOD_CASH)

        # 3. Future due date and CONFIRMED (should be in outstanding, NOT in overdue)
        inv_future = Invoice.objects.create(
            subscription=self.sub,
            period_start=self.today,
            period_end=future_date,
            status=Invoice.STATUS_CONFIRMED,
            total=Decimal("200.00"),
            due_date=future_date,
        )

        # 4. Draft invoice with past due date (should be in overdue, NOT in outstanding)
        inv_draft = Invoice.objects.create(
            subscription=self.sub,
            period_start=past_date - timedelta(days=90),
            period_end=past_date - timedelta(days=60),
            status=Invoice.STATUS_DRAFT,
            total=Decimal("50.00"),
            due_date=past_date,
        )

        overdue_invoices = list(Invoice.objects.overdue())
        self.assertIn(inv_overdue, overdue_invoices)
        self.assertIn(inv_draft, overdue_invoices)
        self.assertNotIn(inv_paid_past, overdue_invoices)
        self.assertNotIn(inv_future, overdue_invoices)

        outstanding_invoices = list(Invoice.objects.outstanding())
        self.assertIn(inv_overdue, outstanding_invoices)
        self.assertIn(inv_future, outstanding_invoices)
        self.assertNotIn(inv_paid_past, outstanding_invoices)
        self.assertNotIn(inv_draft, outstanding_invoices)

    def test_discount_validation_and_calculation(self):
        """Verifies Discount model validations and calculate() logic."""
        # Percentage must be <= 100
        disc_invalid_pct = Discount(name="Over 100", code="ERR101", type=Discount.TYPE_PERCENTAGE, value=Decimal("105.00"))
        with self.assertRaises(ValidationError):
            disc_invalid_pct.clean()

        # Fixed must be > 0
        disc_invalid_fixed = Discount(name="Zero Fixed", code="ERR0", type=Discount.TYPE_FIXED, value=Decimal("0.00"))
        with self.assertRaises(ValidationError):
            disc_invalid_fixed.clean()

        # valid_to >= valid_from
        disc_invalid_dates = Discount(
            name="Date Error",
            code="ERRDATE",
            type=Discount.TYPE_FIXED,
            value=Decimal("10.00"),
            valid_from=self.today,
            valid_to=self.today - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            disc_invalid_dates.clean()

        # Valid percentage discount: 20% off
        disc_pct = Discount.objects.create(
            name="20 Percent Off",
            code="SAVE20",
            type=Discount.TYPE_PERCENTAGE,
            value=Decimal("20.00"),
            is_active=True,
        )
        self.assertEqual(disc_pct.calculate(Decimal("100.00")), Decimal("20.00"))

        # Valid fixed discount: $25 off
        disc_fixed = Discount.objects.create(
            name="25 Off",
            code="SAVE25",
            type=Discount.TYPE_FIXED,
            value=Decimal("25.00"),
            is_active=True,
        )
        self.assertEqual(disc_fixed.calculate(Decimal("100.00")), Decimal("25.00"))
        # Fixed discount never exceeds amount
        self.assertEqual(disc_fixed.calculate(Decimal("15.00")), Decimal("15.00"))

        # Inactive discount returns 0
        disc_fixed.is_active = False
        disc_fixed.save()
        self.assertEqual(disc_fixed.calculate(Decimal("100.00")), Decimal("0.00"))

        # Usage limit reached returns 0
        disc_pct.usage_limit = 1
        disc_pct.times_used = 1
        disc_pct.save()
        self.assertEqual(disc_pct.calculate(Decimal("100.00")), Decimal("0.00"))
