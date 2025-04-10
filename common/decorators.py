from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect


def session_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if session is valid and not expired
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect(settings.LOGIN_URL)
        return view_func(request, *args, **kwargs)

    return wrapper


def active_user_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to continue.")
            return redirect(settings.LOGIN_URL)
        if not request.user.is_active:
            messages.error(request, "Your account is inactive. Please contact support.")
            return redirect(settings.LOGIN_URL)
        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in to continue.")
                return redirect(settings.LOGIN_URL)

            user_type = getattr(request.user, "user_type", None)
            if user_type not in allowed_roles:
                messages.error(request, "Access denied. Insufficient privileges.")
                return redirect("accounts:profile")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
