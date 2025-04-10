import uuid

from django.db.models import Sum
from django.utils import timezone

from notifications.models import Notification

from .models import Order


def generate_order_id():
    """Generate a unique order ID"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def get_buyer_order_stats(buyer):
    """Get statistics about a buyer's orders"""
    orders = Order.objects.filter(buyer=buyer)
    return {
        "total_orders": orders.count(),
        "total_spent": orders.filter(status="DELIVERED").aggregate(Sum("total_price"))[
            "total_price__sum"
        ]
        or 0,
        "active_orders": orders.filter(
            status__in=["CONFIRMED", "IN_PRODUCTION", "READY_FOR_DELIVERY", "SHIPPED"]
        ).count(),
        "completed_orders": orders.filter(status="DELIVERED").count(),
        "cancelled_orders": orders.filter(status="CANCELED").count(),
    }


def process_order_status_change(order, new_status):
    """Handle order status changes and notifications"""
    old_status = order.status
    order.status = new_status
    order.save()

    # Notify buyer
    Notification.objects.create(
        notification_id=f"NTF-{uuid.uuid4().hex[:8].upper()}",
        recipient=order.buyer.user,
        type="ORDER_UPDATE",
        message=f"Your order {order.order_id} has been updated from {old_status} to {new_status}",
    )

    # Notify designer if relevant
    if new_status == "IN_PRODUCTION":
        Notification.objects.create(
            notification_id=f"NTF-{uuid.uuid4().hex[:8].upper()}",
            recipient=order.design.designer.user,
            type="ORDER_UPDATE",
            message=f"Production has started for order {order.order_id}",
        )


def check_order_cancellable(order):
    """Check if an order can be cancelled"""
    non_cancellable_statuses = ["SHIPPED", "DELIVERED"]
    time_limit = timezone.now() - timezone.timedelta(hours=24)

    return (
        order.status not in non_cancellable_statuses and order.date_ordered > time_limit
    )


def validate_order_customizations(design, customizations):
    """Validate that order customizations are valid for the design"""
    if not design.is_customizable():
        return False

    for option, choice in customizations.items():
        option_obj = design.customization_options.filter(name=option).first()
        if not option_obj or choice not in option_obj.available_choices:
            return False
    return True
