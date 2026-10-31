"""
subscriptions/views.py
======================
Purpose:
    Subscription views for customers and staff.
    Uses filter_by_user helper to guarantee that customers only see their own subscriptions.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.utils import filter_by_user
from .models import Subscription


@login_required
def subscription_list_view(request):
    """
    Lists subscriptions.
    - Customers see only their own subscriptions.
    - Staff / Admin see all organization subscriptions.
    """
    queryset = Subscription.objects.select_related("customer", "plan").all()
    subscriptions = filter_by_user(queryset, request.user, user_field="customer")

    return render(
        request,
        "subscriptions/subscription_list.html",
        {"subscriptions": subscriptions},
    )


@login_required
def subscription_detail_view(request, subscription_id):
    """
    Displays single subscription details along with its line items.
    Enforces user-level security via filter_by_user.
    """
    queryset = Subscription.objects.select_related("customer", "plan").prefetch_related("lines__product", "lines__tax")
    scoped_queryset = filter_by_user(queryset, request.user, user_field="customer")
    subscription = get_object_or_404(scoped_queryset, id=subscription_id)

    return render(
        request,
        "subscriptions/subscription_detail.html",
        {"subscription": subscription},
    )
