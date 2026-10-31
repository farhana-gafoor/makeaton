"""
billing/views.py
================
Purpose:
    Invoice views for customers and staff.
    Uses filter_by_user to ensure customers only view their own invoices.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.utils import filter_by_user
from .models import Invoice


@login_required
def invoice_list_view(request):
    """
    Lists invoices.
    - Customers see only their own invoices.
    - Staff / Admin see all organization invoices.
    """
    queryset = Invoice.objects.select_related("subscription__customer", "subscription__plan").all()
    invoices = filter_by_user(queryset, request.user, user_field="subscription__customer")

    return render(request, "billing/invoice_list.html", {"invoices": invoices})


@login_required
def invoice_detail_view(request, invoice_id):
    """
    Displays single invoice detail with line items and payment breakdown.
    Scoped to user permissions.
    """
    queryset = (
        Invoice.objects
        .select_related("subscription__customer", "subscription__plan")
        .prefetch_related("lines__product", "payments")
    )
    scoped_queryset = filter_by_user(queryset, request.user, user_field="subscription__customer")
    invoice = get_object_or_404(scoped_queryset, id=invoice_id)

    return render(request, "billing/invoice_detail.html", {"invoice": invoice})
