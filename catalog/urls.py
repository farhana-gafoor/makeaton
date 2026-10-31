"""
catalog/urls.py
===============
Purpose:
    URL routes for catalog browsing (plans and products).
"""

from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    path("plans/", views.plan_list_view, name="plan_list"),
    path("products/", views.product_list_view, name="product_list"),
]
