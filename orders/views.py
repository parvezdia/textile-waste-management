from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeliveryInfoForm, OrderForm, PaymentInfoForm
from .models import Order


@login_required
def order_list(request):
    if hasattr(request.user, "buyer"):
        orders = Order.objects.filter(buyer=request.user.buyer)
    else:
        orders = Order.objects.all()
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if not request.user.is_staff and order.buyer.user != request.user:
        messages.error(request, "You don't have permission to view this order.")
        return redirect("orders:order_list")
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def create_order(request):
    if not hasattr(request.user, "buyer"):
        messages.error(request, "Only buyers can create orders.")
        return redirect("orders:order_list")

    if request.method == "POST":
        order_form = OrderForm(request.POST)
        payment_form = PaymentInfoForm(request.POST)
        delivery_form = DeliveryInfoForm(request.POST)

        if all(
            [order_form.is_valid(), payment_form.is_valid(), delivery_form.is_valid()]
        ):
            try:
                with transaction.atomic():
                    payment = payment_form.save()
                    delivery = delivery_form.save()
                    order = order_form.save(commit=False)
                    order.buyer = request.user.buyer
                    order.payment_info = payment
                    order.delivery_info = delivery
                    order.total_price = order.calculate_total_price()
                    order.save()

                messages.success(request, "Order created successfully!")
                return redirect("orders:order_detail", order_id=order.order_id)
            except Exception as e:
                messages.error(request, f"Error creating order: {str(e)}")
    else:
        order_form = OrderForm()
        payment_form = PaymentInfoForm()
        delivery_form = DeliveryInfoForm()

    return render(
        request,
        "orders/order_form.html",
        {
            "order_form": order_form,
            "payment_form": payment_form,
            "delivery_form": delivery_form,
        },
    )


@login_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to update order status.")
        return redirect("orders:order_list")

    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.update_status(new_status)
            messages.success(request, f"Order status updated to {new_status}")
        else:
            messages.error(request, "Invalid status")
    return redirect("orders:order_detail", order_id=order.order_id)


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    if order.buyer.user != request.user:
        messages.error(request, "You don't have permission to cancel this order.")
        return redirect("orders:order_list")

    if request.method == "POST":
        if order.cancel_order():
            messages.success(request, "Order cancelled successfully!")
        else:
            messages.error(request, "Order cannot be cancelled at this stage.")
    return redirect("orders:order_detail", order_id=order.order_id)
