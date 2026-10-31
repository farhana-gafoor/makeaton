"""
catalog/models.py
=================
Purpose:
    Catalog data models: Products, Variants, Subscription Plans, Taxes, and Discounts.
    Includes model-level validation:
      - Non-negative prices
      - End date must be on or after start date
      - Percentage values cannot exceed 100%
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Product(models.Model):
    """
    Core item that can be sold standalone or bundled into subscriptions.
    """

    TYPE_SERVICE = "service"
    TYPE_PHYSICAL = "physical"
    TYPE_DIGITAL = "digital"

    TYPE_CHOICES = (
        (TYPE_SERVICE, _("Service")),
        (TYPE_PHYSICAL, _("Physical Good")),
        (TYPE_DIGITAL, _("Digital Software / License")),
    )

    name = models.CharField(max_length=200, help_text=_("Display name of the product."))
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_SERVICE,
        help_text=_("Nature of the product for fulfillment."),
    )
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Customer purchase price (must be >= 0.00)."),
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Internal unit cost for margin calculations (must be >= 0.00)."),
    )
    notes = models.TextField(blank=True, help_text=_("Internal notes or specs."))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return f"{self.name} (${self.sales_price})"

    def clean(self):
        super().clean()
        if self.sales_price is not None and self.sales_price < Decimal("0.00"):
            raise ValidationError({"sales_price": _("Sales price cannot be negative.")})
        if self.cost_price is not None and self.cost_price < Decimal("0.00"):
            raise ValidationError({"cost_price": _("Cost price cannot be negative.")})


class ProductVariant(models.Model):
    """
    Variant of a parent product, such as Brand, Color, Tier, or Storage size.
    Example: Attribute='brand', Value='Odoo', Extra Price=560.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        help_text=_("Parent product for this variant."),
    )
    attribute = models.CharField(
        max_length=100,
        help_text=_("Attribute name (e.g. 'Brand', 'Tier', 'Color')."),
    )
    value = models.CharField(
        max_length=100,
        help_text=_("Attribute option (e.g. 'Odoo', 'Enterprise', 'Blue')."),
    )
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Additional price added to base product sales price (must be >= 0.00)."),
    )

    class Meta:
        unique_together = ("product", "attribute", "value")
        verbose_name = _("Product Variant")
        verbose_name_plural = _("Product Variants")

    def __str__(self):
        if self.extra_price > 0:
            return f"{self.product.name} - {self.attribute}: {self.value} (+${self.extra_price})"
        return f"{self.product.name} - {self.attribute}: {self.value}"

    def clean(self):
        super().clean()
        if self.extra_price is not None and self.extra_price < Decimal("0.00"):
            raise ValidationError({"extra_price": _("Extra price cannot be negative.")})


class Plan(models.Model):
    """
    Recurring subscription plan defining pricing frequency and lifecycle policies.
    """

    PERIOD_DAILY = "daily"
    PERIOD_WEEKLY = "weekly"
    PERIOD_MONTHLY = "monthly"
    PERIOD_YEARLY = "yearly"

    PERIOD_CHOICES = (
        (PERIOD_DAILY, _("Daily")),
        (PERIOD_WEEKLY, _("Weekly")),
        (PERIOD_MONTHLY, _("Monthly")),
        (PERIOD_YEARLY, _("Yearly")),
    )

    name = models.CharField(max_length=150, help_text=_("Plan name (e.g. Pro Monthly)."))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Base recurring fee for this billing period (must be >= 0.00)."),
    )
    billing_period = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        default=PERIOD_MONTHLY,
        help_text=_("How frequently the subscriber is charged."),
    )
    min_quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_("Minimum units required to subscribe to this plan."),
    )
    available_from = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date this plan becomes publicly selectable (optional)."),
    )
    available_to = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date this plan is deprecated/retired (optional)."),
    )

    # Lifecycle and automation flags
    auto_close = models.BooleanField(
        default=False,
        help_text=_("Automatically close when payment is not received within grace period."),
    )
    closable = models.BooleanField(
        default=True,
        help_text=_("Allows customers to cancel/close this subscription on-demand."),
    )
    pausable = models.BooleanField(
        default=True,
        help_text=_("Allows customers or staff to temporarily pause billing."),
    )
    renewable = models.BooleanField(
        default=True,
        help_text=_("Can be automatically renewed when the current period concludes."),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")

    def __str__(self):
        return f"{self.name} (${self.price}/{self.get_billing_period_display()})"

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal("0.00"):
            raise ValidationError({"price": _("Plan price cannot be negative.")})

        # Date range validation: end date after start date
        if self.available_from and self.available_to:
            if self.available_to < self.available_from:
                raise ValidationError({
                    "available_to": _("Plan 'Available To' date must be on or after 'Available From' date.")
                })


class Tax(models.Model):
    """
    Tax rate applied to subscription line items or invoices (e.g. GST, VAT, Sales Tax).
    """

    name = models.CharField(max_length=100, help_text=_("Tax name (e.g. 'GST 18%', 'VAT 5%')."))
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text=_("Tax percentage rate between 0.00% and 100.00%."),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Tax")
        verbose_name_plural = _("Taxes")

    def __str__(self):
        return f"{self.name} ({self.rate}%)"

    def clean(self):
        super().clean()
        if self.rate is not None:
            if self.rate < Decimal("0.00"):
                raise ValidationError({"rate": _("Tax rate cannot be negative.")})
            if self.rate > Decimal("100.00"):
                raise ValidationError({"rate": _("Tax rate cannot exceed 100%.")})


class Discount(models.Model):
    """
    Promotional discounts applicable to products or subscriptions.
    Supports fixed currency deductions or percentage-based discounts.
    """

    TYPE_FIXED = "fixed"
    TYPE_PERCENT = "percent"

    TYPE_CHOICES = (
        (TYPE_FIXED, _("Fixed Amount ($)")),
        (TYPE_PERCENT, _("Percentage (%)")),
    )

    APPLIES_PRODUCTS = "products"
    APPLIES_SUBSCRIPTIONS = "subscriptions"

    APPLIES_CHOICES = (
        (APPLIES_PRODUCTS, _("Specific Products")),
        (APPLIES_SUBSCRIPTIONS, _("Entire Subscription / Invoice")),
    )

    name = models.CharField(max_length=150, help_text=_("Discount code / title (e.g. LAUNCH10)."))
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PERCENT,
        help_text=_("Fixed dollar amount or percentage reduction."),
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Discount amount or percentage rate."),
    )
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Minimum order / subtotal amount required to apply discount."),
    )
    min_quantity = models.PositiveIntegerField(
        default=0,
        help_text=_("Minimum line item quantity required to trigger discount."),
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Validity start date."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Validity expiry date."),
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum total times this coupon can be redeemed across the platform."),
    )
    times_used = models.PositiveIntegerField(
        default=0,
        help_text=_("Current count of redemptions."),
    )
    applies_to = models.CharField(
        max_length=20,
        choices=APPLIES_CHOICES,
        default=APPLIES_SUBSCRIPTIONS,
        help_text=_("Scope: individual products or full subscription billing."),
    )
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="discounts",
        help_text=_("Selected products when 'Applies To' is set to Products."),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")

    def __str__(self):
        suffix = "%" if self.type == self.TYPE_PERCENT else "$"
        return f"{self.name} (-{self.value}{suffix})"

    def clean(self):
        super().clean()
        # 1. Non-negative checks
        if self.value is not None and self.value < Decimal("0.00"):
            raise ValidationError({"value": _("Discount value cannot be negative.")})

        if self.min_purchase is not None and self.min_purchase < Decimal("0.00"):
            raise ValidationError({"min_purchase": _("Minimum purchase cannot be negative.")})

        # 2. Percentage cannot exceed 100%
        if self.type == self.TYPE_PERCENT and self.value is not None and self.value > Decimal("100.00"):
            raise ValidationError({"value": _("Percentage discount cannot exceed 100.00%.")})

        # 3. End date must be on or after start date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({"end_date": _("Discount end date must be on or after start date.")})
