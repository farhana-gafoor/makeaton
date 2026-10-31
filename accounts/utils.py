"""
accounts/utils.py
=================
Purpose:
    Shared security and scoping helper utilities.
    Ensures data isolation between customers while allowing staff/admin oversight.
"""

from django.db.models import QuerySet


def filter_by_user(queryset: QuerySet, user, user_field: str = "customer") -> QuerySet:
    """
    Scopes a QuerySet based on the currently authenticated user's role:
    
    1. Anonymous / Unauthenticated:
       Returns an empty queryset (queryset.none()).
       
    2. Admin / Staff (or Superuser):
       Returns the entire queryset unscoped so internal team can manage all data.
       
    3. Customer:
       Filters the queryset strictly where `user_field == user`. Customers NEVER
       see other customers' subscriptions, invoices, or personal data.

    Parameters:
        queryset (QuerySet): The Django queryset to filter (e.g. Subscription.objects.all()).
        user: The `request.user` instance.
        user_field (str): The field name on the model that references the user (defaults to 'customer').

    Example usage in views:
        subscriptions = filter_by_user(Subscription.objects.all(), request.user)
    """
    if not user or not user.is_authenticated:
        return queryset.none()

    # Admin and staff have organization-wide visibility
    if user.is_superuser or getattr(user, "role", None) in [user.ROLE_ADMIN, user.ROLE_STAFF]:
        return queryset

    # Regular customer: strict ownership filtering
    filter_kwargs = {user_field: user}
    return queryset.filter(**filter_kwargs)
