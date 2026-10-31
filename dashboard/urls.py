"""
dashboard/urls.py
=================
Purpose:
    URL configuration for internal analytics and executive dashboards.
"""

from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("finance/", views.finance_dashboard_view, name="finance"),
]
