"""
dashboard/views.py
==================
Purpose:
    Finance and Executive Analytics Dashboard.
    Provides key metric cards (Active Subscriptions, Revenue Received, Outstanding Balance,
    Overdue Invoices) and paginated invoice logs.

Performance Design Notes:
    - Uses `aggregate(Sum(...))` to compute totals at the database level in a single query.
    - Uses `select_related('subscription__customer', 'subscription__plan')` to eliminate N+1 queries.
    - Uses `Paginator` to slice queries efficiently so thousands of records load instantly.
"""

from decimal import Decimal
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum
from accounts.decorators import role_required
from subscriptions.models import Subscription
from billing.models import Invoice, Payment


@role_required("admin", "staff")
def finance_dashboard_view(request):
    """
    Finance summary dashboard for staff and administrators.
    
    METRICS COMPUTED:
      1. Active Subscriptions Count
      2. Revenue Received (Total settled payments)
      3. Outstanding Amount (Total unpaid invoice balance)
      4. Overdue Invoices Count (via custom Invoice.objects.overdue() query)

    SPEED OPTIMIZATION:
      Always use DB aggregates and select_related instead of Python loops over querysets!
    """

    # 1. Active Subscriptions count (single SQL COUNT query)
    active_subscriptions_count = Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE
    ).count()

    # 2. Total Revenue Received (single SQL SUM query over Payment model)
    revenue_agg = Payment.objects.aggregate(total_revenue=Sum("amount"))
    total_revenue = revenue_agg["total_revenue"] or Decimal("0.00")

    # 3. Total Invoiced Amount vs Total Paid -> Outstanding Balance
    # In large systems, aggregate total invoice sums and paid sums:
    invoices_agg = Invoice.objects.aggregate(total_invoiced=Sum("total"))
    total_invoiced = invoices_agg["total_invoiced"] or Decimal("0.00")
    total_outstanding = max(Decimal("0.00"), total_invoiced - total_revenue)

    # 4. Overdue Invoices QuerySet (computed dynamically via InvoiceQuerySet.overdue())
    overdue_invoices_qs = (
        Invoice.objects.overdue()
        .select_related("subscription__customer", "subscription__plan")
        .order_by("due_date")
    )
    overdue_count = overdue_invoices_qs.count()

    # 5. Recent Invoices table with pagination (15 per page for fast rendering)
    recent_invoices_list = (
        Invoice.objects.all()
        .select_related("subscription__customer", "subscription__plan")
        .order_by("-created_at")
    )
    paginator = Paginator(recent_invoices_list, 15)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "active_subscriptions_count": active_subscriptions_count,
        "total_revenue": total_revenue,
        "total_outstanding": total_outstanding,
        "overdue_count": overdue_count,
        "overdue_invoices": overdue_invoices_qs[:5],  # Top 5 most urgent
        "page_obj": page_obj,
    }

    return render(request, "dashboard/finance.html", context)
