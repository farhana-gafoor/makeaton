"""
catalog/views.py
================
Purpose:
    Catalog presentation views. Provides public plan listing and product overviews.
"""

from django.shortcuts import render
from .models import Plan, Product


def plan_list_view(request):
    """
    Publicly browsable list of available subscription plans.
    """
    plans = Plan.objects.all().order_by("price")
    return render(request, "catalog/plan_list.html", {"plans": plans})


def product_list_view(request):
    """
    Publicly browsable list of products.
    """
    products = Product.objects.all().prefetch_related("variants")
    return render(request, "catalog/product_list.html", {"products": products})
