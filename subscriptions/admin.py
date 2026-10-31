"""
subscriptions/admin.py
======================
Purpose:
    Django admin configuration for QuotationTemplates and Subscriptions.
    Includes inlines for fast multi-line editing.
"""

from django.contrib import admin
from .models import QuotationTemplate, TemplateLine, Subscription, SubscriptionLine


class TemplateLineInline(admin.TabularInline):
    model = TemplateLine
    extra = 1


@admin.register(QuotationTemplate)
class QuotationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "validity_days", "created_at")
    search_fields = ("name",)
    inlines = [TemplateLineInline]


class SubscriptionLineInline(admin.TabularInline):
    model = SubscriptionLine
    extra = 1


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "plan", "status", "start_date", "next_invoice_date")
    list_filter = ("status", "plan", "start_date")
    search_fields = ("number", "customer__email")
    readonly_fields = ("number", "created_at", "updated_at")
    inlines = [SubscriptionLineInline]
