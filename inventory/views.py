from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import factory_required, inventory_manager_required
from .forms import DimensionsForm, TextileWasteForm, WasteReviewForm
from .models import TextileWaste, WasteHistory
from .utils import (
    calculate_storage_efficiency,
    calculate_sustainability_impact,
    export_report_as_excel,
    export_report_as_pdf,
    generate_waste_report,
    get_expiring_inventory,
    get_inventory_metrics,
    get_trends_analysis,
)


@login_required
def waste_list(request):
    waste_items = TextileWaste.objects.all()

    # Filtering
    status = request.GET.get("status")
    if status:
        waste_items = waste_items.filter(status=status)

    # Factory specific view
    if hasattr(request.user, "factorypartner"):
        waste_items = waste_items.filter(factory=request.user.factorypartner)

    # Pagination
    paginator = Paginator(waste_items, 10)
    page = request.GET.get("page")
    waste_items = paginator.get_page(page)

    return render(
        request,
        "inventory/waste_list.html",
        {
            "waste_items": waste_items,
            "status_choices": TextileWaste.WASTE_STATUS_CHOICES,
        },
    )


@login_required
@factory_required
def factory_inventory(request):
    if not hasattr(request.user, "factorypartner"):
        messages.error(
            request, "Access denied. Only factory partners can view inventory."
        )
        return redirect("inventory:waste_list")

    wastes = TextileWaste.objects.filter(factory=request.user.factorypartner)
    return render(request, "inventory/factory_inventory.html", {"wastes": wastes})


@login_required
@factory_required
def upload_waste(request):
    """Handle waste upload with capacity validation and logging"""
    from common.utils import (
        format_capacity_message,
        log_capacity_change,
        validate_capacity_request,
    )

    if request.method == "POST":
        waste_form = TextileWasteForm(request.POST, factory=request.user.factorypartner)
        dimensions_form = DimensionsForm(request.POST)

        if all([waste_form.is_valid(), dimensions_form.is_valid()]):
            factory = request.user.factorypartner
            additional_quantity = float(waste_form.cleaned_data["quantity"])

            # Validate capacity with detailed response
            validation = validate_capacity_request(factory, additional_quantity)

            if not validation["valid"]:
                messages.error(request, validation["message"])
                capacity_info = {
                    "current_usage": validation["current_usage"],
                    "capacity": factory.factory_details.production_capacity,
                    "usage_percentage": (
                        validation["current_usage"]
                        / factory.factory_details.production_capacity
                        * 100
                    )
                    if factory.factory_details.production_capacity
                    else 100,
                    "available": validation["available"],
                    "recommended": factory.factory_details.calculate_recommended_capacity(),
                }
                return render(
                    request,
                    "inventory/upload_waste.html",
                    {
                        "waste_form": waste_form,
                        "dimensions_form": dimensions_form,
                        "capacity_info": capacity_info,
                    },
                )

            # Track old usage for logging
            old_usage = validation["current_usage"]

            waste = waste_form.save(commit=False)
            dimensions = dimensions_form.save()
            waste.dimensions = dimensions
            waste.factory = factory

            # Auto-calculate sustainability score
            waste.sustainability_score = waste.calculate_recycle_potential()
            waste.save()

            # Log capacity change
            new_usage = factory.factory_details.get_current_capacity_usage()
            log_capacity_change(factory, old_usage, new_usage, "waste_upload")

            # Format user message based on new capacity
            capacity_msg = format_capacity_message(
                new_usage,
                factory.factory_details.production_capacity,
                factory.factory_details.production_capacity - new_usage,
            )

            messages.success(
                request,
                f"Waste item {waste.waste_id} has been uploaded successfully. "
                f"{capacity_msg['message']}",
            )
            return redirect("inventory:waste_detail", waste_id=waste.waste_id)
    else:
        waste_form = TextileWasteForm()
        dimensions_form = DimensionsForm()

        # Get initial capacity info with message formatting
        factory = request.user.factorypartner
        current_usage = factory.factory_details.get_current_capacity_usage()
        capacity = factory.factory_details.production_capacity
        available = capacity - current_usage if capacity else 0

        capacity_info = {
            "current_usage": current_usage,
            "capacity": capacity,
            "usage_percentage": (current_usage / capacity * 100) if capacity else 100,
            "available": available,
            "recommended": factory.factory_details.calculate_recommended_capacity(),
            "message": format_capacity_message(current_usage, capacity, available),
        }

    return render(
        request,
        "inventory/upload_waste.html",
        {
            "waste_form": waste_form,
            "dimensions_form": dimensions_form,
            "capacity_info": capacity_info,
        },
    )


@login_required
def waste_detail(request, waste_id):
    waste = get_object_or_404(TextileWaste, waste_id=waste_id)
    history = waste.history.all()

    return render(
        request, "inventory/waste_detail.html", {"waste": waste, "history": history}
    )


@login_required
@inventory_manager_required
def review_waste(request, waste_id):
    waste = get_object_or_404(TextileWaste, waste_id=waste_id)

    if request.method == "POST":
        form = WasteReviewForm(request.POST, instance=waste)
        if form.is_valid():
            waste = form.save(reviewer=request.user)
            waste.update_sustainability_score()
            messages.success(request, "Waste review completed successfully.")
            return redirect("inventory:waste_list")
    else:
        form = WasteReviewForm(instance=waste)

    return render(
        request, "inventory/review_waste.html", {"form": form, "waste": waste}
    )


@login_required
def waste_edit(request, waste_id):
    waste = get_object_or_404(TextileWaste, waste_id=waste_id)

    if (
        not hasattr(request.user, "factorypartner")
        or waste.factory != request.user.factorypartner
    ):
        messages.error(request, "Access denied. You can't edit this waste entry.")
        return redirect("inventory:waste_list")

    if request.method == "POST":
        waste_form = TextileWasteForm(request.POST, instance=waste)
        dimensions_form = DimensionsForm(request.POST, instance=waste.dimensions)

        if all([waste_form.is_valid(), dimensions_form.is_valid()]):
            dimensions_form.save()
            waste = waste_form.save()
            messages.success(request, "Textile waste updated successfully!")
            return redirect("inventory:waste_detail", waste_id=waste.waste_id)
    else:
        waste_form = TextileWasteForm(instance=waste)
        dimensions_form = DimensionsForm(instance=waste.dimensions)

    return render(
        request,
        "inventory/waste_form.html",
        {
            "waste_form": waste_form,
            "dimensions_form": dimensions_form,
            "waste": waste,
            "action": "Edit",
        },
    )


@login_required
def waste_delete(request, waste_id):
    waste = get_object_or_404(TextileWaste, waste_id=waste_id)

    if (
        not hasattr(request.user, "factorypartner")
        or waste.factory != request.user.factorypartner
    ):
        messages.error(request, "Access denied. You can't delete this waste entry.")
        return redirect("inventory:waste_list")

    if request.method == "POST":
        waste.delete()
        messages.success(request, "Textile waste deleted successfully!")
        return redirect("inventory:factory_inventory")

    return render(request, "inventory/waste_confirm_delete.html", {"waste": waste})


@login_required
def inventory_dashboard(request):
    """Dashboard view for inventory management"""
    # Check user type and redirect accordingly
    if request.user.user_type == "FACTORY":
        if not hasattr(request.user, "factorypartner"):
            messages.warning(
                request, "Please complete your factory profile setup first."
            )
            return redirect("accounts:profile_setup")

        # Get statistics for factory dashboard
        queryset = TextileWaste.objects.filter(factory=request.user.factorypartner)

        total_waste = queryset.aggregate(
            total_quantity=Sum("quantity"), total_items=Count("id")
        )

        status_counts = queryset.values("status").annotate(count=Count("id"))

        recent_activities = (
            WasteHistory.objects.select_related("waste_item", "changed_by")
            .filter(waste_item__factory=request.user.factorypartner)
            .order_by("-timestamp")[:10]
        )

        context = {
            "total_waste": total_waste,
            "status_counts": status_counts,
            "recent_activities": recent_activities,
            "user_type": request.user.user_type,
        }

        return render(request, "inventory/dashboard.html", context)
    else:
        # For non-factory users, show the waste list
        return redirect("inventory:waste_list")


@login_required
def factory_history(request):
    if not hasattr(request.user, "factorypartner"):
        messages.error(request, "Access denied. Factory partner only.")
        return redirect("home")

    waste_items = TextileWaste.objects.filter(
        factory=request.user.factorypartner
    ).order_by("-date_added")

    # Filtering
    status = request.GET.get("status")
    if status:
        waste_items = waste_items.filter(status=status)

    # Pagination
    paginator = Paginator(waste_items, 10)
    page = request.GET.get("page")
    waste_items = paginator.get_page(page)

    return render(
        request,
        "inventory/factory_history.html",
        {
            "waste_items": waste_items,
            "status_choices": TextileWaste.WASTE_STATUS_CHOICES,
        },
    )


@login_required
def inventory_analytics(request):
    """Analytics view showing detailed inventory insights"""
    # For factory partners, show only their data
    if hasattr(request.user, "factorypartner"):
        metrics = get_inventory_metrics(factory=request.user.factorypartner)
        efficiency_metrics = calculate_storage_efficiency(factory=request.user.factorypartner)
        
        # Get latest 90 days for trend analytics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)
          # Get trends analysis for this factory (filter the result afterwards)
        trends_data = get_trends_analysis(start_date, end_date)
        
        # Get expiring inventory
        expiring_soon = get_expiring_inventory(days=30, factory=request.user.factorypartner)
        
        return render(
            request,
            "inventory/analytics.html",
            {
                "metrics": metrics,
                "efficiency_metrics": efficiency_metrics,
                "trends": trends_data,
                "expiring_soon": expiring_soon,
                "factory_view": True
            },
        )
    # For admin users with proper permissions, show all data
    elif request.user.has_perm("inventory.can_view_analytics"):
        metrics = get_inventory_metrics()
        efficiency_metrics = calculate_storage_efficiency()
        
        return render(
            request,
            "inventory/analytics.html",
            {"metrics": metrics, "efficiency_metrics": efficiency_metrics},
        )
    else:
        # For other users without permission
        messages.error(request, "You don't have permission to view analytics.")
        return redirect("inventory:dashboard")


@login_required
@permission_required("inventory.can_view_analytics")
def inventory_reports(request):
    """Report generation interface"""
    return render(request, "inventory/reports.html")


@login_required
@permission_required("inventory.can_view_analytics")
def generate_report(request):
    """Generate and display inventory report with export options"""
    # Get date range from request
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    export_format = request.GET.get("format")

    if not (start_date and end_date):
        # Default to last 30 days if no date range specified
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    # Generate report data
    report_data = generate_waste_report(start_date, end_date)

    # Add environmental impact metrics
    report_data["environmental_impact"] = calculate_sustainability_impact(report_data)

    # Add trends analysis
    report_data["trends"] = get_trends_analysis(start_date, end_date)

    # Handle export requests
    if export_format == "pdf":
        pdf_data = export_report_as_pdf(report_data)
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="inventory_report.pdf"'
        return response

    elif export_format == "excel":
        excel_data = export_report_as_excel(report_data)
        response = HttpResponse(
            excel_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="inventory_report.xlsx"'
        return response

    # Display report in HTML format
    return render(
        request,
        "inventory/report_result.html",
        {"report": report_data, "start_date": start_date, "end_date": end_date},
    )


@login_required
@factory_required
def factory_reports(request):
    """Factory-specific reports view"""
    metrics = get_inventory_metrics(factory=request.user.factorypartner)
    efficiency_metrics = calculate_storage_efficiency(
        factory=request.user.factorypartner
    )

    return render(
        request,
        "inventory/factory_reports.html",
        {"metrics": metrics, "efficiency_metrics": efficiency_metrics},
    )


@login_required
@permission_required("inventory.can_generate_reports")
def export_report(request):
    """Export inventory report in selected format"""
    try:
        start_date = datetime.strptime(request.GET.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(request.GET.get("end_date"), "%Y-%m-%d")
        export_format = request.GET.get("format", "html")
    except (TypeError, ValueError):
        messages.error(request, "Invalid date range provided")
        return redirect("inventory:reports")

    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    report_data = generate_waste_report(start_date, end_date, factory)

    # Add sustainability impact data
    impact_data = calculate_sustainability_impact(report_data)
    report_data["environmental_impact"] = impact_data

    # Add trends analysis
    trends_data = get_trends_analysis(start_date, end_date, factory)
    report_data["trends"] = trends_data

    if export_format == "pdf":
        pdf_data = export_report_as_pdf(report_data)
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="inventory_report_{start_date.strftime("%Y%m%d")}.pdf"'
        )
        return response

    elif export_format == "excel":
        excel_data = export_report_as_excel(report_data)
        response = HttpResponse(
            excel_data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="inventory_report_{start_date.strftime("%Y%m%d")}.xlsx"'
        )
        return response

    else:  # HTML format
        return render(request, "inventory/report_result.html", {"report": report_data})


@login_required
@permission_required("inventory.can_view_analytics")
def get_impact_metrics(request):
    """API endpoint for fetching sustainability impact metrics"""
    try:
        start_date = datetime.strptime(request.GET.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(request.GET.get("end_date"), "%Y-%m-%d")
    except (TypeError, ValueError):
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now()

    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    report_data = generate_waste_report(start_date, end_date, factory)
    impact_data = calculate_sustainability_impact(report_data)

    return JsonResponse(impact_data)


@login_required
@permission_required("inventory.can_view_analytics")
def get_trend_metrics(request):
    """API endpoint for fetching trend analysis metrics"""
    try:
        start_date = datetime.strptime(request.GET.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(request.GET.get("end_date"), "%Y-%m-%d")
    except (TypeError, ValueError):
        start_date = timezone.now() - timedelta(days=90)  # Default to last 90 days
        end_date = timezone.now()

    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    trends_data = get_trends_analysis(start_date, end_date, factory)

    return JsonResponse(trends_data, safe=False)


# API Endpoints
@login_required
def get_metrics(request):
    """API endpoint for fetching inventory metrics"""
    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    metrics = get_inventory_metrics(factory=factory)
    return JsonResponse(metrics)


@login_required
def get_storage_efficiency(request):
    """API endpoint for fetching storage efficiency metrics"""
    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    metrics = calculate_storage_efficiency(factory=factory)
    return JsonResponse(metrics)


@login_required
def get_expiring_soon(request):
    """API endpoint for fetching items expiring soon"""
    days = int(request.GET.get("days", 30))
    factory = (
        request.user.factorypartner if hasattr(request.user, "factorypartner") else None
    )
    items = get_expiring_inventory(days=days, factory=factory)

    data = [
        {
            "id": item.waste_id,
            "type": item.type,
            "material": item.material,
            "quantity": item.quantity,
            "expiry_date": item.expiry_date.strftime("%Y-%m-%d"),
            "days_left": (item.expiry_date - timezone.now()).days,
        }
        for item in items
    ]

    return JsonResponse({"items": data})
