"""
accounts/decorators.py
======================
Purpose:
    View decorators and Class-Based View mixins for Role-Based Access Control (RBAC).
    Use these to protect views so only authorized roles (e.g. admin, staff) can access them.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin


def role_required(*allowed_roles):
    """
    Decorator for function-based views to enforce that the logged-in user
    possesses one of the specified roles (e.g., @role_required('admin', 'staff')).

    Behavior:
    1. If user is NOT authenticated: redirects to login URL.
    2. If user is authenticated and is a superuser: always granted access.
    3. If user has one of allowed_roles: access granted.
    4. Otherwise: raises PermissionDenied (HTTP 403) or displays error message.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this page.")
                return redirect("accounts:login")

            # Superusers always pass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check if user role matches any allowed role
            if getattr(request.user, "role", None) in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Access denied for unauthorized role
            messages.error(
                request,
                f"Access denied. This action requires one of the following roles: {', '.join(allowed_roles)}."
            )
            raise PermissionDenied(
                f"User role '{getattr(request.user, 'role', 'unknown')}' is not authorized."
            )

        return _wrapped_view
    return decorator


class RoleRequiredMixin(AccessMixin):
    """
    CBV mixin that restricts access to users possessing any of the roles
    defined in `allowed_roles`.
    
    Example:
        class StaffOnlyView(RoleRequiredMixin, ListView):
            allowed_roles = ['admin', 'staff']
            ...
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser or request.user.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("You do not have permission to access this resource.")
