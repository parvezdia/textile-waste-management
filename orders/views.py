from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
import logging
import json
import os

from .forms import DeliveryInfoForm, OrderForm, PaymentInfoForm
from .models import Order

# Set up custom logger for debugging
logger = logging.getLogger('customization_debug')
logger.setLevel(logging.DEBUG)

# Create log file in the project directory
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'customization_debug.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Create handler and set level
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


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
def create_order(request, design_id=None):
    if not hasattr(request.user, "buyer"):
        messages.error(request, "Only buyers can create orders.")
        return redirect("orders:order_list")
    design = None
    if design_id:
        from designs.models import Design
        design = get_object_or_404(Design, design_id=design_id)
        
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
                      # Apply customizations from session if available
                    customization_data = request.session.get('design_customizations', {})
                    logger.debug(f"Order creation - Session data: {json.dumps(customization_data)}")
                    
                    if customization_data and customization_data.get('design_id') == design_id:
                        customization_options = customization_data.get('options', {})
                        logger.debug(f"Order creation - Applying customizations: {json.dumps(customization_options)}")
                        order.customizations = customization_options
                    else:
                        logger.debug(f"Order creation - No matching customization data found for design_id: {design_id}")
                    
                    # Generate a unique order_id if not provided
                    import uuid
                    if not order.order_id:
                        order.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                    
                    # Calculate price with customizations explicitly
                    base_price = order.design.price
                    logger.debug(f"Order creation - Base price: {base_price}")
                    
                    # Add customization costs
                    if hasattr(order, 'customizations') and order.customizations:
                        logger.debug(f"Order has customizations: {json.dumps(order.customizations)}")
                        # Get all customization options for this design
                        all_options = list(order.design.customization_options.all())
                        logger.debug(f"All available options for design: {[option.name for option in all_options]}")
                        
                        for option_name, choice in order.customizations.items():
                            try:
                                # Find the matching option by name
                                matching_options = [opt for opt in all_options if opt.name == option_name]
                                if matching_options:
                                    option = matching_options[0]
                                    logger.debug(f"Found option: {option.name}, price_impact: {json.dumps(option.price_impact)}")
                                    price_impact = option.price_impact.get(choice, 0)
                                    logger.debug(f"Option '{option_name}': choice '{choice}', impact: {price_impact}")
                                    base_price += price_impact
                                else:
                                    logger.debug(f"Option '{option_name}' not found in design customization options")
                            except Exception as e:
                                logger.debug(f"Error calculating price impact for {option_name}: {str(e)}")
                                logger.exception(e)  # Log full stack trace
                    
                    order.total_price = base_price
                    logger.debug(f"Final price: {order.total_price}")
                    order.save()
                messages.success(request, "Order created successfully!")
                return redirect("orders:order_detail", order_id=order.order_id)
            except Exception as e:
                messages.error(request, f"Error creating order: {str(e)}")
    else:
        initial_data = {}
        if design:
            initial_data['design'] = design.id
        order_form = OrderForm(initial=initial_data)
        payment_form = PaymentInfoForm()
        delivery_form = DeliveryInfoForm()
      # Create context dictionary for both POST and GET requests
    context = {
        "form": order_form,  # Template uses "form" not "order_form"
        "order_form": order_form,  # Keep this for backward compatibility
        "payment_form": payment_form,
        "delivery_form": delivery_form,
    }
    
    if design:
        context["design"] = design        # Calculate customization costs and base price separately
        from decimal import Decimal
        base_price = design.price
        customization_cost_total = Decimal("0.00")
        selected_customizations = []
        
        # Apply customization price impacts if available in session
        customization_data = request.session.get('design_customizations', {})
            
        if customization_data and customization_data.get('design_id') == design_id:
            customization_options = customization_data.get('options', {})
            
            # Get all customization options for this design
            all_options = design.customization_options.all()
            
            # Add price impacts from customizations by iterating through all available options
            for option in all_options:
                option_value = customization_options.get(option.name)
                if option_value:
                    # Calculate price impact based on the CustomizationOption model logic
                    price_impact = Decimal("0.00")
                    
                    if option.price_impact.get("has_impact", False):
                        if option_value in option.price_impact:
                            # If the specific choice has a price impact defined
                            try:
                                impact_value = option.price_impact.get(option_value)
                                if impact_value is not None:
                                    if isinstance(impact_value, str):
                                        price_impact = Decimal(impact_value)
                                    else:
                                        price_impact = Decimal(str(impact_value))
                            except:
                                # Fallback to type-based calculation
                                if option.type == "COLOR":
                                    price_impact = round(base_price * Decimal("0.05"), 2)
                                elif option.type == "SIZE":
                                    price_impact = round(base_price * Decimal("0.10"), 2)
                        else:
                            # Use the calculated additional_cost based on option type
                            if option.type == "COLOR":
                                price_impact = round(base_price * Decimal("0.05"), 2)
                            elif option.type == "SIZE":
                                price_impact = round(base_price * Decimal("0.10"), 2)
                    
                    # Add to total customization cost
                    customization_cost_total += price_impact
                    
                    # Store selected customization details for display
                    selected_customizations.append({
                        'name': option.name,
                        'type': option.type,
                        'value': option_value,
                        'price_impact': price_impact
                    })
        
        # Store both base price and customization costs separately for dynamic calculation in the template
        context["base_price"] = base_price
        context["customization_cost"] = customization_cost_total
        context["unit_price"] = base_price + customization_cost_total
        context["estimated_total"] = base_price + customization_cost_total
        context["selected_customizations"] = selected_customizations
        
        # Store the session customization data for form submission
        context["customization_data"] = customization_data
        
    return render(request, "orders/order_form.html", context)


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
