from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def designer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "designer"):
            messages.error(request, "Access denied. Designer privileges required.")
            return redirect("designs:design_list")
        return view_func(request, *args, **kwargs)

    return wrapper


def approved_designer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "designer"):
            messages.error(request, "Access denied. Designer privileges required.")
            return redirect("designs:design_list")
        if not request.user.designer.is_approved:
            messages.warning(
                request,
                "Your designer account is pending approval. Please wait for admin approval.",
                extra_tags='warning swal'
            )
            return redirect("accounts:profile_setup")
        return view_func(request, *args, **kwargs)
    return wrapper


def can_manage_design(view_func):
    @wraps(view_func)
    def wrapper(request, design_id=None, *args, **kwargs):
        if not hasattr(request.user, "designer"):
            messages.error(request, "Access denied. Designer privileges required.")
            return redirect("designs:design_list")

        if design_id:
            design = request.user.designer.designs.filter(design_id=design_id).first()
            if not design:
                messages.error(
                    request, "Access denied. You can only manage your own designs."
                )
                return redirect("designs:design_list")

        return view_func(request, design_id, *args, **kwargs)

    return wrapper


def can_customize_design(view_func):
    @wraps(view_func)
    def wrapper(request, design_id, *args, **kwargs):
        if not hasattr(request.user, "buyer"):
            messages.error(request, "Access denied. Buyer privileges required.")
            return redirect("designs:design_list")

        return view_func(request, design_id, *args, **kwargs)

    return wrapper
