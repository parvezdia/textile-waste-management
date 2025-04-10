from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

User = get_user_model()


def factory_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is factory type first
        if not request.user.user_type == "FACTORY":
            messages.error(
                request, "Access denied. Factory partner privileges required."
            )
            return redirect("accounts:profile")

        # Get user with all related data in a single query
        try:
            user = User.objects.select_related(
                "contact_info", "factorypartner", "factorypartner__factory_details"
            ).get(id=request.user.id)

            factory_partner = getattr(user, "factorypartner", None)
            factory_details = (
                factory_partner.factory_details if factory_partner else None
            )
            contact_info = user.contact_info

            # Check if required fields are populated
            profile_complete = (
                factory_partner is not None
                and factory_details is not None
                and factory_details.factory_name
                and contact_info is not None
                and contact_info.address
                and contact_info.phone
            )

            if profile_complete:
                return view_func(request, *args, **kwargs)
            else:
                messages.warning(request, "Please complete your factory profile setup.")
                return redirect("accounts:profile_setup")

        except (User.DoesNotExist, AttributeError):
            messages.warning(request, "Please complete your factory profile setup.")
            return redirect("accounts:profile_setup")

    return wrapper


def can_manage_waste(view_func):
    @wraps(view_func)
    def wrapper(request, waste_id=None, *args, **kwargs):
        if not hasattr(request.user, "factorypartner"):
            messages.error(
                request, "Access denied. Factory partner privileges required."
            )
            return redirect("inventory:waste_list")

        if waste_id:
            waste = request.user.factorypartner.waste_inventory.filter(
                waste_id=waste_id
            ).first()
            if not waste:
                messages.error(
                    request,
                    "Access denied. You can only manage your own waste inventory.",
                )
                return redirect("inventory:waste_list")

        return view_func(request, waste_id, *args, **kwargs)

    return wrapper


def inventory_manager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.has_perm("inventory.can_manage_inventory"):
            messages.error(
                request, "Access denied. Inventory manager privileges required."
            )
            return redirect("inventory:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper
