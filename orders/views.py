from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
import logging
import json
import os

from .forms import DeliveryInfoForm, OrderForm, PaymentInfoForm
from .models import Order, PaymentInfo, DeliveryInfo

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
    # Get status filter from query parameters
    status_filter = request.GET.get('status')
    
    # Filter orders based on user type
    if hasattr(request.user, "buyer"):
        orders = Order.objects.filter(buyer=request.user.buyer)
    elif hasattr(request.user, "designer"):
        # For designers, only show orders for their designs
        orders = Order.objects.filter(design__designer=request.user.designer)
    else:
        # Staff can see all orders
        orders = Order.objects.all()
    
    # Apply status filter if provided
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Order by most recent first
    orders = orders.order_by('-date_ordered')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        "orders": orders,
        "status_filter": status_filter,
        "status_choices": Order.ORDER_STATUS_CHOICES,
    }
    return render(request, "orders/order_list.html", context)


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
        logger.debug(f"Found design with ID {design_id}: {design.name} (internal ID: {design.id})")
      
    if request.method == "POST":
        logger.debug(f"Order creation POST request received - Data: {request.POST}")
        
        # Create a mutable copy of POST data
        post_data = request.POST.copy()
        
        # Make sure we have a quantity
        if not post_data.get('quantity'):
            post_data['quantity'] = '1'
            logger.debug("Added default quantity of 1")
        
        # Ensure design ID is correctly set
        if design and not post_data.get('design'):
            post_data['design'] = design.id
            logger.debug(f"Added design ID from URL parameter: {design.id}")
        
        # Add submit_order if not present (to ensure form processing)
        if 'submit_order' not in post_data:
            post_data['submit_order'] = '1'
            logger.debug("Added submit_order parameter")
            
        # Initialize order form with modified data
        order_form = OrderForm(post_data)
        logger.debug(f"Form initialized with data: {post_data}")
          # Add customization data from session
        customization_data = request.session.get('design_customizations', {})
        if design_id and customization_data and str(customization_data.get('design_id')) == str(design_id):
            customization_options = customization_data.get('options', {})
            # Always ensure we have proper JSON for customizations
            try:
                # Make data mutable if needed
                post_data = post_data.copy() if hasattr(post_data, 'copy') else post_data
                
                # Replace the form's customization data with properly JSON-encoded data
                post_data['customizations'] = json.dumps(customization_options)
                
                # Re-initialize the form with the updated data
                order_form = OrderForm(post_data)
                logger.debug(f"Added customizations to form as JSON: {json.dumps(customization_options)}")
            except Exception as e:
                logger.debug(f"Error adding customizations to form: {str(e)}")
        
        # Process form if valid
        if order_form.is_valid():
            logger.debug("Form is valid, proceeding with order creation")
            try:
                with transaction.atomic():
                    # Create dummy payment and delivery info for now
                    # In a production system, these would be properly collected
                    import uuid
                    from datetime import timedelta, date
                    
                    # Create payment info
                    payment = PaymentInfo(
                        payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
                        method="CREDIT_CARD",
                        amount=0.0,  # Will be updated with order total
                        status="PENDING"
                    )
                    payment.save()
                    
                    # Create delivery info with estimated delivery in 14 days if not available from design
                    estimated_delivery = date.today() + timedelta(days=14)
                    if design and hasattr(design, 'get_estimated_delivery_date'):
                        estimated_delivery = design.get_estimated_delivery_date()
                    
                    # Get shipping address from buyer profile if available
                    shipping_address = "Address to be updated"
                    if hasattr(request.user.buyer, 'shipping_address'):
                        shipping_address = request.user.buyer.shipping_address or shipping_address
                    
                    delivery = DeliveryInfo(
                        tracking_number=f"TRK-{uuid.uuid4().hex[:8].upper()}",
                        carrier="Standard Delivery",
                        address=shipping_address,
                        estimated_delivery_date=estimated_delivery
                    )
                    delivery.save()
                    
                    # Create order                    # Create the order object but don't save it yet
                    order = order_form.save(commit=False)
                    order.buyer = request.user.buyer
                    order.payment_info = payment
                    order.delivery_info = delivery
                    
                    # Make sure design is correctly set
                    if not order.design and design:
                        order.design = design
                        logger.debug(f"Set design directly on order object: {design.design_id}")
                    
                    # Ensure customizations is always a dict
                    if not order.customizations:
                        order.customizations = {}
                        
                    # If we have customizations in the form, use those (already handled by the form)
                    # If not, check the session data
                    if not order.customizations and design_id:
                        customization_data = request.session.get('design_customizations', {})
                        logger.debug(f"Order creation - Session data: {json.dumps(customization_data)}")
                        
                        if customization_data and str(customization_data.get('design_id')) == str(design_id):
                            customization_options = customization_data.get('options', {})
                            logger.debug(f"Order creation - Applying customizations: {json.dumps(customization_options)}")
                            order.customizations = customization_options
                        else:
                            logger.debug(f"Order creation - No matching customization data found for design_id: {design_id}")
                            # Initialize with empty dict to prevent None issues
                            order.customizations = {}
                      # Generate a unique order_id if not provided
                    if not order.order_id:
                        # Make sure the order ID is unique
                        while True:
                            new_order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                            if not Order.objects.filter(order_id=new_order_id).exists():
                                order.order_id = new_order_id
                                break
                              # Calculate price based on quantity and customizations
                    base_price = getattr(design, 'price', 0)
                    if not base_price and hasattr(design, 'get_price'):
                        base_price = design.get_price()
                    
                    quantity = order.quantity or 1
                    logger.debug(f"Order creation - Base price: {base_price}, Quantity: {quantity}")
                    
                    # Apply customization costs if any
                    customization_cost = 0
                    if hasattr(order, 'customizations') and order.customizations:
                        logger.debug(f"Order has customizations: {json.dumps(order.customizations)}")
                        # Get all customization options for this design
                        all_options = list(design.customization_options.all())
                        logger.debug(f"All available options for design: {[option.name for option in all_options]}")
                        
                        for option_name, choice in order.customizations.items():
                            try:
                                # Find the matching option by name
                                matching_options = [opt for opt in all_options if opt.name == option_name]
                                if matching_options:
                                    option = matching_options[0]
                                    logger.debug(f"Found option: {option.name}, price_impact: {option.price_impact}")
                                    price_impact = option.price_impact.get(choice, 0)
                                    logger.debug(f"Option '{option_name}': choice '{choice}', impact: {price_impact}")
                                    customization_cost += price_impact
                                else:
                                    logger.debug(f"Option '{option_name}' not found in design customization options")
                            except Exception as e:
                                logger.debug(f"Error calculating price impact for {option_name}: {str(e)}")
                                logger.exception(e)  # Log full stack trace
                    
                    # Calculate total price with quantity
                    unit_price = base_price + customization_cost
                    order.total_price = unit_price * quantity
                    
                    # Update payment amount to match order total
                    payment.amount = order.total_price
                    payment.save()
                    
                    logger.debug(f"Final price: {order.total_price}")
                    order.save()
                    
                    # Clear session customization data after successful order
                    if 'design_customizations' in request.session:
                        del request.session['design_customizations']
                    
                messages.success(request, "Order placed successfully! You can track your order status here.")
                return redirect("orders:order_detail", order_id=order.order_id)            
            except Exception as e:
                logger.exception(f"Error creating order: {str(e)}")
                messages.error(request, f"Error placing order: {str(e)}")
        else:
            # If form is not valid, log the errors
            logger.debug(f"Form validation errors: {order_form.errors}")
            for field, errors in order_form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        initial_data = {}
        if design:
            initial_data['design'] = design.id
            
            # Pre-populate customizations from session if available
            customization_data = request.session.get('design_customizations', {})
            if customization_data and str(customization_data.get('design_id')) == str(design_id):
                customization_options = customization_data.get('options', {})
                initial_data['customizations'] = customization_options
                
        order_form = OrderForm(initial=initial_data)
        payment_form = PaymentInfoForm()
        delivery_form = DeliveryInfoForm()# Create context dictionary for both POST and GET requests
    context = {
        "form": order_form,  # Template uses "form" not "order_form"
        "order_form": order_form,  # Keep this for backward compatibility
        "payment_form": payment_form if 'payment_form' in locals() else None,
        "delivery_form": delivery_form if 'delivery_form' in locals() else None,
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
