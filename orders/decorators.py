from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import Order


def buyer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "buyer"):
            messages.error(request, "Access denied. Buyer privileges required.")
            return redirect("orders:order_list")
        return view_func(request, *args, **kwargs)

    return wrapper


def can_manage_order(view_func):
    @wraps(view_func)
    def wrapper(request, order_id=None, *args, **kwargs):
        if order_id:
            order = Order.objects.filter(order_id=order_id).first()
            if not order:
                messages.error(request, "Order not found.")
                return redirect("orders:order_list")

            # Allow access to buyer who placed the order
            is_buyer = (
                hasattr(request.user, "buyer") and order.buyer == request.user.buyer
            )
            # Allow access to designer of the ordered design
            is_designer = (
                hasattr(request.user, "designer")
                and order.design.designer == request.user.designer
            )
            # Allow access to admin
            is_admin = request.user.is_staff or hasattr(request.user, "admin")

            if not (is_buyer or is_designer or is_admin):
                messages.error(
                    request,
                    "Access denied. You don't have permission to manage this order.",
                )
                return redirect("orders:order_list")

        return view_func(request, order_id, *args, **kwargs)

    return wrapper


def can_update_order_status(view_func):
    @wraps(view_func)
    def wrapper(request, order_id, *args, **kwargs):
        if not (request.user.is_staff or hasattr(request.user, "admin")):
            messages.error(
                request, "Access denied. Only administrators can update order status."
            )
            return redirect("orders:order_list")

        return view_func(request, order_id, *args, **kwargs)

    return wrapper


def can_cancel_order(view_func):
    @wraps(view_func)
    def wrapper(request, order_id, *args, **kwargs):
        order = Order.objects.filter(order_id=order_id).first()
        if not order:
            messages.error(request, "Order not found.")
            return redirect("orders:order_list")

        if not hasattr(request.user, "buyer") or order.buyer != request.user.buyer:
            messages.error(
                request, "Access denied. Only the buyer can cancel their order."
            )
            return redirect("orders:order_list")

        if order.status in ["SHIPPED", "DELIVERED"]:
            messages.error(request, "Cannot cancel order at this stage.")
            return redirect("orders:order_detail", order_id=order_id)

        return view_func(request, order_id, *args, **kwargs)

    return wrapper
