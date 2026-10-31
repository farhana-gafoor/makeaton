"""
catalog/admin.py
================
Purpose:
    Django admin configuration for catalog entities:
    Products, Variants, Plans, Taxes, and Discounts.
"""

from django.contrib import admin
from .models import Product, ProductVariant, Plan, Tax, Discount


class ProductVariantInline(admin.TabularInline):
    """
    Allows adding and editing variants directly on the parent Product change page.
    """
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "sales_price", "cost_price", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("name", "notes")
    inlines = [ProductVariantInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "attribute", "value", "extra_price")
    list_filter = ("attribute",)
    search_fields = ("product__name", "attribute", "value")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "billing_period", "min_quantity", "auto_close", "renewable")
    list_filter = ("billing_period", "auto_close", "renewable", "pausable")
    search_fields = ("name",)


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ("name", "rate")
    search_fields = ("name",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "value", "applies_to", "times_used", "usage_limit", "start_date", "end_date")
    list_filter = ("type", "applies_to")
    search_fields = ("name",)
    filter_horizontal = ("products",)
