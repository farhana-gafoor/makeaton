"""
subscriptions/models.py
=======================
Purpose:
    Core subscription and quotation models.
    Implements a strict finite state machine for subscription lifecycle:
      Draft -> Quotation -> Confirmed -> Active -> Closed
    Enforces status transitions via a centralized dictionary and change_status() method.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from catalog.models import Plan, Product, Tax


class QuotationTemplate(models.Model):
    """
    Predefined bundle / template used to generate quotes and subscriptions quickly.
    """

    name = models.CharField(max_length=150, help_text=_("Template title (e.g. Starter SaaS Bundle)."))
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="quotation_templates",
        help_text=_("Default plan linked to this template."),
    )
    validity_days = models.PositiveIntegerField(
        default=30,
        help_text=_("Number of days a quotation generated from this template remains valid."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Quotation Template")
        verbose_name_plural = _("Quotation Templates")

    def __str__(self):
        return f"{self.name} ({self.plan.name})"


class TemplateLine(models.Model):
    """
    Line item inside a Quotation Template specifying default products and quantities.
    """

    template = models.ForeignKey(
        QuotationTemplate,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="template_lines",
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("Template Line")
        verbose_name_plural = _("Template Lines")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Subscription(models.Model):
    """
    Customer subscription contract.
    Tracks billing cadence, contract dates, and current lifecycle state.
    """

    # Lifecycle state machine states
    STATUS_DRAFT = "Draft"
    STATUS_QUOTATION = "Quotation"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_ACTIVE = "Active"
    STATUS_CLOSED = "Closed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Draft")),
        (STATUS_QUOTATION, _("Quotation")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_ACTIVE, _("Active")),
        (STATUS_CLOSED, _("Closed")),
    )

    # ==========================================================================
    # Centralized Transition Dictionary
    # ==========================================================================
    # Defines ALL allowed state moves in ONE single place for clarity.
    ALLOWED_TRANSITIONS = {
        STATUS_DRAFT: [STATUS_QUOTATION, STATUS_CLOSED],
        STATUS_QUOTATION: [STATUS_CONFIRMED, STATUS_DRAFT, STATUS_CLOSED],
        STATUS_CONFIRMED: [STATUS_ACTIVE, STATUS_CLOSED],
        STATUS_ACTIVE: [STATUS_CLOSED],
        STATUS_CLOSED: [],  # Closed is terminal
    }

    # Unique human-readable identifier (e.g. SUB-202610-A1B2)
    number = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        help_text=_("Unique auto-generated subscription number."),
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        db_index=True,  # Indexed for fast customer lookups
        help_text=_("Subscriber account (Customer)."),
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        help_text=_("Chosen subscription plan."),
    )

    start_date = models.DateField(default=timezone.localdate)
    expiry_date = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(
        max_length=100,
        default="Immediate",
        help_text=_("Payment terms (e.g. 'Immediate', 'Net 15', 'Net 30')."),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,  # Indexed for fast filtering by active/draft state
    )

    next_invoice_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,  # Indexed for automated recurring billing runner
        help_text=_("Next date when the billing runner should generate an invoice."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")

    def __str__(self):
        return f"{self.number} - {self.customer.email} [{self.status}]"

    def save(self, *args, **kwargs):
        # Auto-generate unique number on first creation
        if not self.number:
            date_prefix = timezone.now().strftime("%Y%m")
            random_suffix = uuid.uuid4().hex[:6].upper()
            self.number = f"SUB-{date_prefix}-{random_suffix}"
        super().save(*args, **kwargs)

    def change_status(self, new_status: str, save: bool = True):
        """
        Transitions the subscription to a new status.
        Rejects invalid moves based on ALLOWED_TRANSITIONS by raising a ValidationError.
        
        Example:
            subscription.change_status('Active')
        """
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                _(f"Invalid status transition from '{self.status}' to '{new_status}'. "
                  f"Allowed target states are: {allowed or 'None (Terminal state)'}")
            )

        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])


class SubscriptionLine(models.Model):
    """
    Individual recurring product/service item within a Subscription.
    """

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="subscription_lines",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.ForeignKey(
        Tax,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscription_lines",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Total price for this line (quantity * unit_price)."),
    )

    class Meta:
        verbose_name = _("Subscription Line")
        verbose_name_plural = _("Subscription Lines")

    def __str__(self):
        return f"{self.product.name} ({self.quantity} @ ${self.unit_price})"

    def clean(self):
        super().clean()
        if self.unit_price is not None and self.quantity is not None:
            # Auto-calculate amount if not explicitly provided
            self.amount = Decimal(str(self.quantity)) * self.unit_price
