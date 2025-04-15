from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, models
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
import json
import xlsxwriter
from io import BytesIO
import datetime

from .forms import (
    AdminForm,
    BuyerForm,
    ContactInfoForm,
    DesignerForm,
    FactoryDetailsForm,
    LoginForm,
    UserRegistrationForm,
)
from .models import Admin, AdminLevel, Buyer, ContactInfo, Designer, FactoryDetails, FactoryPartner, User


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Specify the backend explicitly
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Show appropriate message based on user type
            if user.user_type == "DESIGNER":
                messages.info(
                    request, 
                    'Your designer account has been created and is pending admin approval. '
                    'You will be prompted to complete your profile once approved.'
                )
                return redirect("designs:design_list")
            else:
                messages.success(request, "Registration successful! Please complete your profile.")

            return redirect("accounts:profile_setup")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            try:
                user = User.objects.select_related(
                    "contact_info", "factorypartner", "factorypartner__factory_details",
                    "designer", "admin"
                ).get(email=email)

                if user.check_password(password):
                    login(
                        request,
                        user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )

                    # Check if designer is approved but profile incomplete
                    if user.user_type == "DESIGNER" and hasattr(user, "designer"):
                        designer = user.designer
                        contact_info = user.contact_info
                        
                        if not designer.is_approved:
                            messages.warning(
                                request,
                                "Your designer account is pending approval. "
                                "You will be notified once your account is approved.",
                            )
                            return redirect("designs:design_list")
                        elif not all([
                            contact_info and contact_info.address and contact_info.phone
                        ]):
                            messages.info(
                                request,
                                "Please complete your profile to start using your approved designer account.",
                            )
                            return redirect("accounts:profile_setup")
                        else:
                            return redirect("designs:designer_dashboard")

                    messages.success(request, "Login successful!")

                    # For factory users, check complete profile
                    if user.user_type == "FACTORY":
                        factory_partner = getattr(user, "factorypartner", None)
                        if factory_partner:
                            factory_details = factory_partner.factory_details
                            contact_info = user.contact_info

                            if (
                                factory_details
                                and factory_details.factory_name
                                and contact_info
                                and contact_info.address
                                and contact_info.phone
                            ):
                                return redirect("inventory:dashboard")

                        messages.warning(
                            request, "Please complete your factory profile setup."
                        )
                        return redirect("accounts:profile_setup")

                    # For buyers
                    elif user.user_type == "BUYER":
                        if hasattr(user, "buyer"):
                            return redirect("designs:design_list")
                        else:
                            return redirect("accounts:profile_setup")
                            
                    # For admin users
                    elif user.user_type == "ADMIN":
                        # Check if admin profile exists and is complete
                        admin_profile = getattr(user, "admin", None)
                        contact_info = user.contact_info
                        if admin_profile and contact_info and contact_info.address and contact_info.phone:
                            return redirect("accounts:admin_dashboard")  # Redirect to admin dashboard
                        else:
                            messages.warning(request, "Please complete your admin profile setup.")
                            return redirect("accounts:profile_setup")

                    return redirect("accounts:profile")
                else:
                    messages.error(request, "Invalid email or password")
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("accounts:login")


@login_required
def profile(request):
    user = request.user
    try:
        # Check based on user type
        if user.user_type == "FACTORY":
            factory_partner = user.factorypartner
            factory_details = factory_partner.factory_details
            contact_info = user.contact_info

            # Ensure all required data exists
            if not all(
                [
                    factory_details and factory_details.factory_name,
                    contact_info and contact_info.address and contact_info.phone,
                ]
            ):
                messages.warning(request, "Please complete your factory profile setup")
                return redirect("accounts:profile_setup")

            profile_data = factory_partner

        elif user.user_type == "DESIGNER":
            profile_data = user.designer
        elif user.user_type == "BUYER":
            profile_data = user.buyer
        elif user.user_type == "ADMIN":
            try:
                profile_data = user.admin
                # Ensure contact info is complete
                contact_info = user.contact_info
                if not contact_info or not contact_info.address or not contact_info.phone:
                    messages.warning(request, "Please complete your admin profile setup")
                    return redirect("accounts:profile_setup")
            except (AttributeError, ObjectDoesNotExist):
                messages.warning(request, "Please complete your admin profile setup")
                return redirect("accounts:profile_setup")
        else:
            messages.warning(request, "Invalid user type")
            return redirect("accounts:profile_setup")

        if profile_data is None:
            raise ObjectDoesNotExist

    except (ObjectDoesNotExist, AttributeError):
        messages.warning(request, "Please complete your profile setup")
        return redirect("accounts:profile_setup")    # Prepare context for template
    context = {
        "user": user,
        "profile": profile_data
    }
    
    # Add specific data for designers
    if user.user_type == "DESIGNER" and hasattr(profile_data, 'portfolio'):
        # Count published designs
        from designs.models import Design
        published_designs_count = Design.objects.filter(
            designer=profile_data,
            status="PUBLISHED"
        ).count()
        context["published_designs_count"] = published_designs_count
        
    return render(request, "accounts/profile.html", context)


@login_required
def profile_setup(request):
    user = request.user
    profile_form = None  # Initialize profile_form with a default value

    # Check if profile is already complete for factory users
    if user.user_type == "FACTORY":
        try:
            factory_partner = user.factorypartner
            factory_details = factory_partner.factory_details
            contact_info = user.contact_info

            if all([
                factory_details and factory_details.factory_name,
                contact_info and contact_info.address and contact_info.phone
            ]):
                return redirect("inventory:dashboard")
        except (AttributeError, ObjectDoesNotExist):
            pass
    
    # Check if profile is complete for approved designers
    elif user.user_type == "DESIGNER" and hasattr(user, "designer"):
        designer = user.designer
        contact_info = user.contact_info
        # Only redirect if this is not an edit request
        if designer.is_approved and all([
            contact_info and contact_info.address and contact_info.phone
        ]) and request.GET.get('edit') != 'true':
            return redirect("designs:designer_dashboard")
    
    # Check if profile is complete for admin users
    elif user.user_type == "ADMIN" and hasattr(user, "admin"):
        contact_info = user.contact_info
        if contact_info and contact_info.address and contact_info.phone:
            return redirect("accounts:admin_dashboard")  # Redirect to admin dashboard

    if request.method == "POST":
        contact_form = ContactInfoForm(request.POST, instance=user.contact_info)

        # Get or initialize contact info for all user types
        if not user.contact_info:
            contact_info = ContactInfo()
        else:
            contact_info = user.contact_info
            
        if user.user_type == "FACTORY":
            # Get or initialize factory partner and details
            try:
                factory_partner = user.factorypartner
                factory_details = factory_partner.factory_details
            except (AttributeError, ObjectDoesNotExist):
                factory_details = FactoryDetails()
                factory_partner = None

            factory_details_form = FactoryDetailsForm(
                request.POST, prefix="factory_details", instance=factory_details
            )

            if all([contact_form.is_valid(), factory_details_form.is_valid()]):
                try:
                    with transaction.atomic():
                        # Save contact info and link to user
                        contact_info = contact_form.save()
                        user.contact_info = contact_info
                        user.save()

                        # Save factory details
                        factory_details = factory_details_form.save()

                        # Create or update factory partner
                        if not factory_partner:
                            factory_partner = FactoryPartner.objects.create(
                                user=user, factory_details=factory_details
                            )
                        else:
                            factory_partner.factory_details = factory_details
                            factory_partner.save()

                    messages.success(request, "Factory profile updated successfully!")
                    return redirect("inventory:dashboard")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")
            else:
                if not contact_form.is_valid():
                    messages.error(
                        request,
                        "Please correct the errors in your contact information.",
                    )
                if not factory_details_form.is_valid():
                    messages.error(
                        request, "Please correct the errors in your factory details."
                    )

        elif user.user_type == "DESIGNER":
            try:
                designer_instance = user.designer
            except (AttributeError, ObjectDoesNotExist):
                designer_instance = None
                
            profile_form = DesignerForm(request.POST, instance=designer_instance)
            if contact_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        contact_info = contact_form.save()
                        user.contact_info = contact_info
                        user.save()
                        
                        designer_profile = profile_form.save(commit=False)
                        if not designer_instance:
                            designer_profile.user = user
                        designer_profile.save()
                        
                        messages.success(request, "Designer profile updated successfully!")
                        return redirect("designs:designer_dashboard")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")

        elif user.user_type == "BUYER":
            try:
                buyer_instance = user.buyer
            except (AttributeError, ObjectDoesNotExist):
                buyer_instance = None
                
            profile_form = BuyerForm(request.POST, instance=buyer_instance)
            if contact_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        contact_info = contact_form.save()
                        user.contact_info = contact_info
                        user.save()
                        
                        buyer_profile = profile_form.save(commit=False)
                        if not buyer_instance:
                            buyer_profile.user = user
                        buyer_profile.save()
                        
                        messages.success(request, "Buyer profile updated successfully!")
                        return redirect("designs:design_list")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")
                    
        elif user.user_type == "ADMIN":
            # Handle admin profile setup
            try:
                admin_instance = user.admin
            except (AttributeError, ObjectDoesNotExist):
                admin_instance = None
                
            profile_form = AdminForm(request.POST, instance=admin_instance)
            if contact_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        contact_info = contact_form.save()
                        user.contact_info = contact_info
                        user.save()
                        
                        admin_profile = profile_form.save(commit=False)
                        if not admin_instance:
                            admin_profile.user = user
                        admin_profile.save()
                        
                        messages.success(request, "Admin profile updated successfully!")
                        return redirect("accounts:admin_dashboard")  # Redirect to admin dashboard
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")
        else:
            messages.error(request, "Invalid user type")
            return redirect("accounts:login")
    else:
        contact_form = ContactInfoForm(instance=user.contact_info)

        if user.user_type == "FACTORY":
            try:
                factory_partner = user.factorypartner
                factory_details = factory_partner.factory_details
            except (AttributeError, ObjectDoesNotExist):
                factory_details = None

            factory_details_form = FactoryDetailsForm(
                prefix="factory_details", instance=factory_details
            )

            return render(
                request,
                "accounts/profile_setup.html",
                {
                    "contact_form": contact_form,
                    "factory_details_form": factory_details_form,
                    "user": user,
                },
            )
        elif user.user_type == "DESIGNER":
            try:
                designer_instance = user.designer
            except (AttributeError, ObjectDoesNotExist):
                designer_instance = None
            profile_form = DesignerForm(instance=designer_instance)
        elif user.user_type == "BUYER":
            try:
                buyer_instance = user.buyer
            except (AttributeError, ObjectDoesNotExist):
                buyer_instance = None
            profile_form = BuyerForm(instance=buyer_instance)
        elif user.user_type == "ADMIN":
            # Get or create Admin profile form
            try:
                admin_instance = user.admin
            except (AttributeError, ObjectDoesNotExist):
                admin_instance = None
                
            # Always create a default admin profile if one doesn't exist
            if admin_instance is None:
                with transaction.atomic():
                    admin_instance = Admin.objects.create(
                        user=user,
                        admin_level=AdminLevel.JUNIOR  # Default level
                    )
                    
            profile_form = AdminForm(instance=admin_instance)
        else:
            messages.error(request, "Invalid user type")
            return redirect("accounts:login")

    return render(
        request,
        "accounts/profile_setup.html",
        {"contact_form": contact_form, "profile_form": profile_form, "user": user},
    )


def designer_profile(request, designer_id):
    """View a designer's public profile."""
    from accounts.models import Designer
    from designs.models import Design
    from django.shortcuts import get_object_or_404
    
    # Fetch the designer by their ID
    designer = get_object_or_404(Designer, id=designer_id)
    
    # Get their published designs
    designs = Design.objects.filter(
        designer=designer, 
        status="PUBLISHED"
    ).order_by('-date_created')
    
    context = {
        "designer": designer,
        "designs": designs,
        "designs_count": designs.count(),
    }
    
    return render(request, "accounts/designer_profile.html", context)


# Admin dashboard and related views
@login_required
def admin_dashboard(request):
    """Admin dashboard with overview of system statistics"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    # Get stats for dashboard
    from inventory.models import TextileWaste
    from designs.models import Design
    from orders.models import Order
    
    # Factory stats
    factory_count = FactoryPartner.objects.count()
    waste_count = TextileWaste.objects.count()
    available_waste = TextileWaste.objects.filter(status="AVAILABLE").aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Designer stats
    designer_count = Designer.objects.count()
    pending_designers = Designer.objects.filter(is_approved=False).count()
    design_count = Design.objects.count()
    
    # Buyer stats
    from .models import Buyer
    buyer_count = Buyer.objects.count()
    order_count = Order.objects.count()
    pending_orders = Order.objects.filter(status__in=["PENDING", "PROCESSING"]).count()
    
    context = {
        'user': user,
        'factory_count': factory_count,
        'waste_count': waste_count,
        'available_waste': available_waste,
        'designer_count': designer_count,
        'pending_designers': pending_designers,
        'design_count': design_count,
        'buyer_count': buyer_count,
        'order_count': order_count,
        'pending_orders': pending_orders,
    }
    
    return render(request, "accounts/admin/dashboard.html", context)

@login_required
def admin_factory_waste(request):
    """Admin view to approve and manage factory waste"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    from inventory.models import TextileWaste
    
    # Get all waste items sorted by status (pending first)
    waste_items = TextileWaste.objects.select_related(
        'factory', 'factory__user', 'factory__factory_details', 'dimensions'
    ).order_by(
        '-status', '-date_added'
    )
    
    context = {
        'user': user,
        'waste_items': waste_items,
    }
    
    return render(request, "accounts/admin/factory_waste.html", context)

@login_required
def admin_approve_waste(request, waste_id):
    """Approve a factory waste item"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        return JsonResponse({"status": "error", "message": "Access denied"})
    
    from inventory.models import TextileWaste
    
    waste_item = get_object_or_404(TextileWaste, id=waste_id)
    
    # Update status to approved
    waste_item.status = "AVAILABLE"
    waste_item.save()
    
    # Add notification for factory
    from notifications.utils import create_notification
    create_notification(
        waste_item.factory.user,
        f"Your waste item '{waste_item.material}' has been approved by admin.",
        "waste_approved",
        object_id=waste_item.id
    )
    
    return JsonResponse({
        "status": "success", 
        "message": "Waste item approved successfully"
    })

@login_required
def admin_reject_waste(request, waste_id):
    """Reject a factory waste item"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        return JsonResponse({"status": "error", "message": "Access denied"})
    
    reason = request.POST.get('reason', 'Not specified')
    
    from inventory.models import TextileWaste
    
    waste_item = get_object_or_404(TextileWaste, id=waste_id)
    
    # Update status to rejected
    waste_item.status = "REJECTED"
    waste_item.save()
    
    # Add notification for factory
    from notifications.utils import create_notification
    create_notification(
        waste_item.factory.user,
        f"Your waste item '{waste_item.material}' was rejected. Reason: {reason}",
        "waste_rejected",
        object_id=waste_item.id
    )
    
    return JsonResponse({
        "status": "success", 
        "message": "Waste item rejected successfully"
    })

@login_required
def admin_designers(request):
    """Admin view to approve and manage designers"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    # Get all designers, pending first
    designers = Designer.objects.select_related('user').order_by('is_approved', '-approval_date')
    
    from designs.models import Design
    
    # Get design counts for each designer
    for designer in designers:
        designer.design_count = Design.objects.filter(designer=designer).count()
        designer.published_count = Design.objects.filter(
            designer=designer, status="PUBLISHED"
        ).count()
    
    context = {
        'user': user,
        'designers': designers,
    }
    
    return render(request, "accounts/admin/designers.html", context)

@login_required
def admin_approve_designer(request, designer_id):
    """Approve a designer account"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        return JsonResponse({"status": "error", "message": "Access denied"})
    
    designer = get_object_or_404(Designer, id=designer_id)
    
    # Approve the designer
    designer.is_approved = True
    designer.approval_date = timezone.now()
    designer.save()
    
    # Add notification for designer
    from notifications.utils import create_notification
    create_notification(
        designer.user,
        "Congratulations! Your designer account has been approved.",
        "designer_approved"
    )
    
    return JsonResponse({
        "status": "success", 
        "message": "Designer approved successfully"
    })

@login_required
def admin_designer_designs(request, designer_id):
    """View designs from a specific designer"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    designer = get_object_or_404(Designer, id=designer_id)
    
    from designs.models import Design
    designs = Design.objects.filter(designer=designer).order_by('-date_created')
    
    context = {
        'user': user,
        'designer': designer,
        'designs': designs,
    }
    
    return render(request, "accounts/admin/designer_designs.html", context)

@login_required
def admin_orders(request):
    """Admin view to manage orders and payments"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    from orders.models import Order
    
    # Get all orders, sorted by status and date
    orders = Order.objects.select_related(
        'buyer', 'buyer__user', 'design', 'design__designer'
    ).order_by('status', '-date_ordered')
    
    context = {
        'user': user,
        'orders': orders,
    }
    
    return render(request, "accounts/admin/orders.html", context)

@login_required
def admin_update_order_status(request, order_id):
    """Update the status of an order"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        return JsonResponse({"status": "error", "message": "Access denied"})
    
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid request method"})
    
    from orders.models import Order
    order = get_object_or_404(Order, id=order_id)
    
    status = request.POST.get('status')
    if status not in ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]:
        return JsonResponse({"status": "error", "message": "Invalid status"})
    
    # Update order status
    order.status = status
    order.save()
    
    # Add notification for buyer
    from notifications.utils import create_notification
    create_notification(
        order.buyer.user,
        f"Your order #{order.id} status has been updated to {status}.",
        "order_status_update",
        object_id=order.id
    )
    
    return JsonResponse({
        "status": "success",
        "message": f"Order status updated to {status}"
    })

@login_required
def admin_approve_payment(request, order_id):
    """Approve a payment for an order"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        return JsonResponse({"status": "error", "message": "Access denied"})
    
    from orders.models import Order, Payment
    order = get_object_or_404(Order, id=order_id)
    
    # Find associated payment
    try:
        payment = Payment.objects.get(order=order)
        payment.is_verified = True
        payment.verification_date = timezone.now()
        payment.verified_by = user
        payment.save()
        
        # Update order status to processing
        order.status = "PROCESSING"
        order.save()
        
        # Create notification
        from notifications.utils import create_notification
        create_notification(
            order.buyer.user,
            f"Your payment for order #{order.id} has been verified. Your order is being processed.",
            "payment_approved",
            object_id=order.id
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Payment approved successfully"
        })
    except Payment.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "No payment found for this order"
        })

@login_required
def admin_analytics(request):
    """Admin analytics dashboard"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    # Factory analytics - Material Type Distribution
    from inventory.models import TextileWaste
    waste_by_material = TextileWaste.objects.values('material').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')
    
    # Designer analytics - Design Status Distribution
    from designs.models import Design
    designs_by_status = Design.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Buyer analytics - Order Status Distribution
    from orders.models import Order
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Monthly order revenue
    months = 6  # Last 6 months
    end_date = timezone.now()
    start_date = end_date - datetime.timedelta(days=30*months)
    
    monthly_orders = []
    for i in range(months):
        month_start = start_date + datetime.timedelta(days=30*i)
        month_end = start_date + datetime.timedelta(days=30*(i+1))
        
        month_data = Order.objects.filter(
            date_ordered__gte=month_start,
            date_ordered__lt=month_end
        ).aggregate(
            count=Count('id'),
            revenue=Sum('total_price')
        )
        
        monthly_orders.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_data['count'] or 0,
            'revenue': month_data['revenue'] or 0
        })
    
    # Get top factories by waste quantity (for the table section)
    top_factories = FactoryPartner.objects.select_related('factory_details').annotate(
        total_quantity=Sum('waste_items__quantity'),
        available_quantity=Sum('waste_items__quantity', filter=models.Q(waste_items__status="AVAILABLE")),
        recycled_quantity=Sum('waste_items__quantity', filter=models.Q(waste_items__status="RECYCLED"))
    ).order_by('-total_quantity')[:5]
    
    # Calculate percentages
    for factory in top_factories:
        if factory.total_quantity:
            factory.available_percent = (factory.available_quantity or 0) / factory.total_quantity * 100
            factory.recycled_percent = (factory.recycled_quantity or 0) / factory.total_quantity * 100
        else:
            factory.available_percent = 0
            factory.recycled_percent = 0
    
    context = {
        'user': user,
        'waste_by_material': waste_by_material,
        'designs_by_status': designs_by_status,
        'orders_by_status': orders_by_status,
        'monthly_orders': monthly_orders,
        'top_factories': top_factories,
    }
    
    return render(request, "accounts/admin/analytics.html", context)

@login_required
def admin_sustainability(request):
    """Admin sustainability metrics"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    from inventory.models import TextileWaste
    
    # Calculate textile waste recycled
    total_waste = TextileWaste.objects.aggregate(total=Sum('quantity'))['total'] or 0
    recycled_waste = TextileWaste.objects.filter(status="RECYCLED").aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Calculate CO2 reduction (estimated 6kg CO2 saved per kg textile recycled)
    co2_reduction = recycled_waste * 6  # in kg
    
    # Calculate water savings (estimated 10,000L water saved per kg textile recycled)
    water_savings = recycled_waste * 10000  # in liters
    
    # Calculate percentages for progress bars
    recycled_percentage = (recycled_waste / total_waste * 100) if total_waste > 0 else 0
    co2_percentage = min((co2_reduction / 1000 * 100), 100)  # Cap at 100%
    water_percentage = min((water_savings / 100000 * 100), 100)  # Cap at 100%
    
    # Calculate environmental impact equivalents
    co2_reduction_trees = co2_reduction / 21  # Each tree absorbs ~21kg CO2 per year
    water_savings_households = water_savings / 350  # Average household uses ~350L per day
    
    # Get waste utilization rate by factory
    waste_by_factory = TextileWaste.objects.values(
        'factory__factory_details__factory_name'
    ).annotate(
        total=Sum('quantity'),
        recycled=Sum('quantity', filter=models.Q(status="RECYCLED")),
        utilization_rate=models.F('recycled') * 100.0 / models.F('total')
    ).order_by('-total')
    
    context = {
        'user': user,
        'total_waste': total_waste,
        'recycled_waste': recycled_waste,
        'co2_reduction': co2_reduction,
        'water_savings': water_savings,
        'waste_by_factory': waste_by_factory,
        'recycled_percentage': recycled_percentage,
        'co2_percentage': co2_percentage,
        'water_percentage': water_percentage,
        'co2_reduction_trees': co2_reduction_trees,
        'water_savings_households': water_savings_households,
    }
    
    return render(request, "accounts/admin/sustainability.html", context)

@login_required
def generate_sustainability_report(request):
    """Generate Excel report with sustainability metrics"""
    user = request.user
    
    # Verify user is admin
    if user.user_type != "ADMIN":
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("accounts:profile")
    
    # Create an in-memory output file
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    
    # Add formatting
    title_format = workbook.add_format({
        'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#4CAF50', 'font_color': 'white'
    })
    header_format = workbook.add_format({
        'bold': True, 'font_size': 12, 'align': 'center', 'bg_color': '#8BC34A', 'font_color': 'white'
    })
    data_format = workbook.add_format({'align': 'center'})
    percent_format = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
    
    # Add overall metrics worksheet
    metrics_sheet = workbook.add_worksheet('Sustainability Metrics')
    metrics_sheet.set_column('A:C', 25)
    
    from inventory.models import TextileWaste
    
    # Calculate textile waste recycled
    total_waste = TextileWaste.objects.aggregate(total=Sum('quantity'))['total'] or 0
    recycled_waste = TextileWaste.objects.filter(status="RECYCLED").aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Calculate CO2 reduction (estimated 6kg CO2 saved per kg textile recycled)
    co2_reduction = recycled_waste * 6  # in kg
    
    # Calculate water savings (estimated 10,000L water saved per kg textile recycled)
    water_savings = recycled_waste * 10000  # in liters
    
    # Add title
    metrics_sheet.merge_range('A1:C1', 'Textile Waste Sustainability Report', title_format)
    metrics_sheet.write_row(1, 0, ['Metric', 'Value', 'Unit'], header_format)
    
    # Add data
    metrics_data = [
        ['Total Waste Collected', total_waste, 'kg'],
        ['Waste Recycled', recycled_waste, 'kg'],
        ['Recycling Rate', recycled_waste/total_waste if total_waste > 0 else 0, ''],
        ['Estimated CO2 Reduction', co2_reduction, 'kg'],
        ['Water Savings', water_savings, 'liters'],
        ['Water Savings', water_savings/1000, 'm³'],
    ]
    
    for i, row in enumerate(metrics_data):
        if i == 2:  # Recycling rate row
            metrics_sheet.write(i+2, 0, row[0], data_format)
            metrics_sheet.write(i+2, 1, row[1], percent_format)
            metrics_sheet.write(i+2, 2, row[2], data_format)
        else:
            metrics_sheet.write_row(i+2, 0, row, data_format)
    
    # Add factory breakdown worksheet
    factory_sheet = workbook.add_worksheet('Factory Breakdown')
    factory_sheet.set_column('A:E', 20)
    
    factory_sheet.merge_range('A1:E1', 'Factory Waste Utilization Breakdown', title_format)
    factory_sheet.write_row(1, 0, [
        'Factory Name', 'Total Waste (kg)', 'Recycled (kg)', 'Available (kg)', 'Utilization Rate'
    ], header_format)
    
    # Get waste by factory
    waste_by_factory = TextileWaste.objects.values(
        'factory__factory_details__factory_name'
    ).annotate(
        total=Sum('quantity'),
        recycled=Sum('quantity', filter=models.Q(status="RECYCLED")),
        available=Sum('quantity', filter=models.Q(status="AVAILABLE"))
    ).order_by('-total')
    
    # Add factory data
    for i, factory in enumerate(waste_by_factory):
        factory_name = factory['factory__factory_details__factory_name'] or 'Unknown'
        total = factory['total'] or 0
        recycled = factory['recycled'] or 0
        available = factory['available'] or 0
        utilization_rate = recycled/total if total > 0 else 0
        
        factory_sheet.write(i+2, 0, factory_name, data_format)
        factory_sheet.write(i+2, 1, total, data_format)
        factory_sheet.write(i+2, 2, recycled, data_format)
        factory_sheet.write(i+2, 3, available, data_format)
        factory_sheet.write(i+2, 4, utilization_rate, percent_format)
    
    # Add material breakdown worksheet
    material_sheet = workbook.add_worksheet('Material Breakdown')
    material_sheet.set_column('A:D', 20)
    
    material_sheet.merge_range('A1:D1', 'Waste by Material Type', title_format)
    material_sheet.write_row(1, 0, [
        'Material Type', 'Quantity (kg)', 'Percentage of Total'
    ], header_format)
    
    # Get waste by material type
    waste_by_material = TextileWaste.objects.values('material').annotate(
        total=Sum('quantity')
    ).order_by('-total')
    
    # Add material data
    for i, material in enumerate(waste_by_material):
        material_type = material['material']
        total = material['total'] or 0
        percentage = total/total_waste if total_waste > 0 else 0
        
        material_sheet.write(i+2, 0, material_type, data_format)
        material_sheet.write(i+2, 1, total, data_format)
        material_sheet.write(i+2, 2, percentage, percent_format)
    
    # Add monthly trends worksheet
    trends_sheet = workbook.add_worksheet('Monthly Trends')
    trends_sheet.set_column('A:C', 20)
    
    trends_sheet.merge_range('A1:C1', 'Monthly Waste Collection Trends', title_format)
    trends_sheet.write_row(1, 0, ['Month', 'Waste Collected (kg)', 'Waste Recycled (kg)'], header_format)
    
    # Get monthly waste data for the last 12 months
    months = 12
    end_date = timezone.now()
    start_date = end_date - datetime.timedelta(days=30*months)
    
    monthly_data = []
    for i in range(months):
        month_start = start_date + datetime.timedelta(days=30*i)
        month_end = start_date + datetime.timedelta(days=30*(i+1))
        
        month_data = TextileWaste.objects.filter(
            date_added__gte=month_start,
            date_added__lt=month_end
        ).aggregate(
            collected=Sum('quantity'),
            recycled=Sum('quantity', filter=models.Q(status="RECYCLED"))
        )
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'collected': month_data['collected'] or 0,
            'recycled': month_data['recycled'] or 0
        })
    
    # Add monthly data
    for i, month in enumerate(monthly_data):
        trends_sheet.write(i+2, 0, month['month'], data_format)
        trends_sheet.write(i+2, 1, month['collected'], data_format)
        trends_sheet.write(i+2, 2, month['recycled'], data_format)
    
    # Close the workbook
    workbook.close()
    
    # Create the HttpResponse with Excel
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=sustainability_report.xlsx'
    
    return response
