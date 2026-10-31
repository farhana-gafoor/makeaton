"""
billing/urls.py
===============
Purpose:
    URL routes for invoice management and viewing.
"""

from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("", views.invoice_list_view, name="list"),
    path("<int:invoice_id>/", views.invoice_detail_view, name="detail"),
]
