"""
billing/models.py
=================
Purpose:
    Billing, Invoicing, and Payment models for BrightLoop.
    Enforces financial invariants:
      - Unique constraint on (subscription, period_start) to prevent duplicate billing
      - Finite state machine for invoice statuses (Draft -> Confirmed -> Paid)
      - Dynamic calculations for amount_paid and balance_due (never stored stale)
      - Queryset helper for overdue invoices (computed dynamically via query)
      - Payment validation (strictly positive, cannot exceed remaining balance)
"""

import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from catalog.models import Product
from subscriptions.models import Subscription


class InvoiceQuerySet(models.QuerySet):
    """
    Custom QuerySet for Invoice model providing domain-specific filters.
    """

    def overdue(self):
        """
        Returns all invoices where due_date < today AND status != 'Paid'.
        Calculated dynamically via SQL query — never stored as a stale column!
        """
        today = timezone.localdate()
        return self.filter(due_date__lt=today).exclude(status=Invoice.STATUS_PAID)

    def unpaid(self):
        """Returns all confirmed or draft invoices that have not been fully settled."""
        return self.exclude(status=Invoice.STATUS_PAID)


class InvoiceManager(models.Manager):
    """Custom manager exposing custom QuerySet methods directly on Invoice.objects."""

    def get_queryset(self):
        return InvoiceQuerySet(self.model, using=self._db)

    def overdue(self):
        return self.get_queryset().overdue()


class Invoice(models.Model):
    """
    Billing statement generated for a specific subscription period.
    """

    STATUS_DRAFT = "Draft"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_PAID = "Paid"
    STATUS_CANCELLED = "Cancelled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Draft")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_PAID, _("Paid")),
        (STATUS_CANCELLED, _("Cancelled")),
    )

    # Allowed status transitions dictionary
    ALLOWED_TRANSITIONS = {
        STATUS_DRAFT: [STATUS_CONFIRMED, STATUS_CANCELLED],
        STATUS_CONFIRMED: [STATUS_PAID, STATUS_CANCELLED],
        STATUS_PAID: [],  # Terminal state
        STATUS_CANCELLED: [],  # Terminal state
    }

    number = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        help_text=_("Unique invoice reference number (e.g. INV-202610-0012)."),
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="invoices",
        help_text=_("Subscription associated with this bill."),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )

    period_start = models.DateField(
        help_text=_("Beginning of this billing cycle."),
    )
    period_end = models.DateField(
        help_text=_("Conclusion of this billing cycle."),
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    due_date = models.DateField(
        help_text=_("Payment deadline date."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InvoiceManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        constraints = [
            # CRITICAL INVARIANT: Prevents double-billing the same subscription for the same billing cycle!
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                name="unique_subscription_period_billing",
            )
        ]

    def __str__(self):
        return f"{self.number} ({self.subscription.customer.email}) - ${self.total} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.number:
            date_prefix = timezone.now().strftime("%Y%m")
            random_suffix = uuid.uuid4().hex[:6].upper()
            self.number = f"INV-{date_prefix}-{random_suffix}"
        super().save(*args, **kwargs)

    def change_status(self, new_status: str, save: bool = True):
        """
        Moves the invoice to the target status.
        Rejects invalid transitions according to ALLOWED_TRANSITIONS.
        """
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                _(f"Invalid invoice transition from '{self.status}' to '{new_status}'. "
                  f"Allowed target states are: {allowed or 'None (Terminal)'}")
            )
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])

    # ==========================================================================
    # Dynamic Financial Properties (Always accurate, never cached in DB)
    # ==========================================================================
    @property
    def amount_paid(self) -> Decimal:
        """Total payments successfully recorded against this invoice."""
        aggregated = self.payments.aggregate(total=Sum("amount"))
        return aggregated["total"] or Decimal("0.00")

    @property
    def balance_due(self) -> Decimal:
        """Remaining outstanding amount on this invoice (Total - Paid)."""
        balance = self.total - self.amount_paid
        return max(Decimal("0.00"), balance)

    @property
    def is_overdue(self) -> bool:
        """True if past due date and not marked as Paid."""
        return self.status != self.STATUS_PAID and self.due_date < timezone.localdate()


class InvoiceLine(models.Model):
    """
    Itemized charge on an Invoice.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_lines",
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Tax rate applied as percentage (e.g. 18.00)."),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=_("Line total before tax and line discounts."),
    )

    class Meta:
        verbose_name = _("Invoice Line")
        verbose_name_plural = _("Invoice Lines")

    def __str__(self):
        return f"{self.description} ({self.quantity} @ ${self.unit_price})"


class Payment(models.Model):
    """
    Payment receipt applied toward an Invoice.
    """

    METHOD_CREDIT_CARD = "credit_card"
    METHOD_BANK_TRANSFER = "bank_transfer"
    METHOD_UPI = "upi"
    METHOD_STRIPE = "stripe"
    METHOD_CASH = "cash"

    METHOD_CHOICES = (
        (METHOD_CREDIT_CARD, _("Credit Card")),
        (METHOD_BANK_TRANSFER, _("Bank Transfer / ACH")),
        (METHOD_UPI, _("UPI / Instant Transfer")),
        (METHOD_STRIPE, _("Stripe Online")),
        (METHOD_CASH, _("Cash / Direct Deposit")),
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
        default=METHOD_CREDIT_CARD,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Payment amount in USD/currency."),
    )
    date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True, help_text=_("Transaction reference or gateway ID."))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return f"Payment #{self.id} for {self.invoice.number} - ${self.amount} via {self.get_method_display()}"

    def clean(self):
        """
        Payment validation:
          1. Amount must be positive (> 0.00).
          2. Amount cannot exceed the remaining balance due on the invoice.
        """
        super().clean()

        if self.amount is not None and self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": _("Payment amount must be strictly greater than zero.")})

        # Check against invoice balance if invoice is attached
        if self.invoice_id and self.amount is not None:
            # If editing an existing payment, exclude self from current payments calculation
            current_paid = self.invoice.payments.exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            current_balance = self.invoice.total - current_paid

            if self.amount > current_balance:
                raise ValidationError({
                    "amount": _(
                        f"Payment amount (${self.amount}) exceeds the remaining invoice balance (${current_balance})."
                    )
                })

    def save(self, *args, **kwargs):
        # Enforce validation on save
        self.full_clean()
        super().save(*args, **kwargs)

        # Automatically mark invoice as Paid if balance reaches zero
        if self.invoice.balance_due <= Decimal("0.00") and self.invoice.status == Invoice.STATUS_CONFIRMED:
            self.invoice.status = Invoice.STATUS_PAID
            self.invoice.save(update_fields=["status", "updated_at"])
