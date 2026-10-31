"""
subscriptions/urls.py
=====================
Purpose:
    URL routes for viewing subscription contracts and details.
"""

from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("", views.subscription_list_view, name="list"),
    path("<int:subscription_id>/", views.subscription_detail_view, name="detail"),
]
