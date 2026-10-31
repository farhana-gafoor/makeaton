"""
billing/admin.py
================
Purpose:
    Django admin configuration for Invoices, Invoice Lines, and Payments.
    Includes inlines for fast inspection of line items and payment transactions.
"""

from django.contrib import admin
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "subscription",
        "status",
        "subtotal",
        "discount_amount",
        "tax_amount",
        "total",
        "amount_paid",
        "balance_due",
        "due_date",
        "is_overdue",
    )
    list_filter = ("status", "due_date", "period_start")
    search_fields = ("number", "subscription__number", "subscription__customer__email")
    readonly_fields = ("number", "created_at", "updated_at", "amount_paid", "balance_due", "is_overdue")
    inlines = [InvoiceLineInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "method", "amount", "date", "created_at")
    list_filter = ("method", "date")
    search_fields = ("invoice__number", "invoice__subscription__customer__email", "note")
    readonly_fields = ("created_at",)
