from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg
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
        efficiency_metrics = calculate_storage_efficiency(
            factory=request.user.factorypartner
        )

        # Get latest 90 days for trend analytics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)
        # Get trends analysis for this factory (filter the result afterwards)
        trends_data = get_trends_analysis(start_date, end_date)

        # Get expiring inventory
        expiring_soon = get_expiring_inventory(
            days=30, factory=request.user.factorypartner
        )

        return render(
            request,
            "inventory/analytics.html",
            {
                "metrics": metrics,
                "efficiency_metrics": efficiency_metrics,
                "trends": trends_data,
                "expiring_soon": expiring_soon,
                "factory_view": True,
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
def inventory_reports(request):
    """Report generation interface with support for factory partners"""
    # Check if the user is a factory partner and adjust permissions accordingly
    if hasattr(request.user, "factorypartner"):
        # Get date range from request if available
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        # Get factory's inventory metrics for dashboard display
        metrics = get_inventory_metrics(factory=request.user.factorypartner)
        efficiency_metrics = calculate_storage_efficiency(
            factory=request.user.factorypartner
        )
        
        # Add sustainability score to metrics - with improved calculation
        base_query = TextileWaste.objects.filter(factory=request.user.factorypartner)
        
        # Only use items with non-zero sustainability scores to avoid skewing the average
        sustainability_data = base_query.filter(sustainability_score__gt=0).aggregate(
            avg=Avg("sustainability_score"),
            count=Count("id")
        )
        
        avg_sustainability = sustainability_data["avg"] or 0
        
        # If we have no items with sustainability scores, check if we have any items at all
        if avg_sustainability == 0 and base_query.exists():
            # Set a default value if there are items but none have sustainability scores
            avg_sustainability = 50  # Default middle value on 0-100 scale
            
        # Convert from 0-100 scale to 0-10 scale for display
        metrics["avg_sustainability"] = avg_sustainability / 10
        
        # Get default date ranges for the report form
        default_end_date = timezone.now()
        default_start_date = default_end_date - timedelta(days=30)

        context = {
            "metrics": metrics,
            "efficiency_metrics": efficiency_metrics,
            "default_start_date": default_start_date.strftime("%Y-%m-%d"),
            "default_end_date": default_end_date.strftime("%Y-%m-%d"),
            "factory_view": True,
        }

        # If exporting a report
        if request.GET.get("action") == "export":
            try:
                # Create naive datetime objects without timezone info
                start_date = datetime.strptime(
                    request.GET.get("start_date"), "%Y-%m-%d"
                )
                end_date = datetime.strptime(request.GET.get("end_date"), "%Y-%m-%d")

                # Add one day to end_date to include the full day
                end_date = datetime.combine(end_date.date(), datetime.max.time())

                export_format = request.GET.get("format", "html")

                # Validate date ranges
                today = timezone.now().date()
                if start_date.date() > end_date.date():
                    messages.error(request, "Start date cannot be after end date.")
                    return render(request, "inventory/reports.html", context)

                if end_date.date() > today:
                    messages.error(request, "End date cannot be in the future.")
                    return render(request, "inventory/reports.html", context)

            except (TypeError, ValueError):
                messages.error(request, "Invalid date range provided")
                return render(request, "inventory/reports.html", context)

            try:
                # Generate report data specific to this factory
                # Use naive datetime objects for the query
                factory = request.user.factorypartner
                report_data = generate_waste_report(start_date, end_date, factory)

                # Add sustainability impact data
                impact_data = calculate_sustainability_impact(report_data)
                report_data["environmental_impact"] = impact_data

                # Add trends analysis
                trends_data = get_trends_analysis(start_date, end_date, factory)
                report_data["trends"] = trends_data

                if export_format == "excel":
                    try:
                        excel_data = export_report_as_excel(report_data)
                        response = HttpResponse(
                            excel_data,
                            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        response["Content-Disposition"] = (
                            f'attachment; filename="factory_report_{start_date.strftime("%Y%m%d")}.xlsx"'
                        )
                        return response
                    except Exception as e:
                        import traceback

                        error_details = traceback.format_exc()
                        print(f"Excel Export Error: {error_details}")
                        messages.error(
                            request, f"Error generating Excel report: {str(e)}"
                        )
                        return render(request, "inventory/reports.html", context)

                else:  # HTML preview
                    context["report"] = report_data
                    context["start_date"] = start_date
                    context["end_date"] = end_date
                    return render(request, "inventory/report_result.html", context)

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                print(f"Report Generation Error: {error_details}")
                messages.error(request, f"Error generating report: {str(e)}")
                return render(request, "inventory/reports.html", context)

        # Regular view - show the report generation form
        return render(request, "inventory/reports.html", context)

    # For admin users with proper permissions
    elif request.user.has_perm("inventory.can_view_analytics"):
        return render(request, "inventory/reports.html")

    else:
        # For other users without permission
        messages.error(request, "You don't have permission to generate reports.")
        return redirect("inventory:dashboard")


@login_required
@factory_required
def factory_reports(request):
    """Factory-specific reports view"""
    # Get basic metrics from existing utility functions
    metrics = get_inventory_metrics(factory=request.user.factorypartner)
    
    # Get factory's waste items
    factory_waste = TextileWaste.objects.filter(factory=request.user.factorypartner)
    
    # Create status distribution with counts and quantities
    status_distribution = factory_waste.values('status').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('status')
    
    # Generate monthly trend data for the past 12 months
    end_date = timezone.now()
    start_date = end_date - timedelta(days=365)  # Past year
    
    # Get monthly data
    monthly_data = []
    monthly_labels = []
    
    # Create a list of the past 12 months
    for i in range(12):
        month_end = end_date - timedelta(days=30 * i)
        month_start = month_end - timedelta(days=30)
        month_count = factory_waste.filter(date_added__range=[month_start, month_end]).count()
        
        # Format month for display (e.g., "Jan 2025")
        month_label = month_start.strftime("%b %Y")
        
        monthly_data.append(month_count)
        monthly_labels.append(month_label)
    
    # Reverse the lists to show oldest to newest
    monthly_data.reverse()
    monthly_labels.reverse()
    
    # Convert data to JSON strings for direct use in JavaScript
    import json
    monthly_data_json = json.dumps(monthly_data)
    monthly_labels_json = json.dumps(monthly_labels)

    return render(
        request,
        "inventory/factory_reports.html",
        {
            "metrics": metrics,
            "status_distribution": status_distribution,
            "monthly_data": monthly_data_json,
            "monthly_labels": monthly_labels_json,
        }
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


@login_required
def get_recent_activities(request):
    """API endpoint for fetching recent activities"""
    # For factory partners, show only their activities
    if hasattr(request.user, "factorypartner"):
        activities = (
            WasteHistory.objects.select_related("waste_item", "changed_by")
            .filter(waste_item__factory=request.user.factorypartner)
            .order_by("-timestamp")[:10]
        )
        
        # Get the updated status counts for the dashboard
        queryset = TextileWaste.objects.filter(factory=request.user.factorypartner)
        status_counts = queryset.values("status").annotate(count=Count("id"))
        
        # Convert status counts to a dictionary for easier access in JavaScript
        status_dict = {}
        for item in status_counts:
            status_dict[item['status']] = item['count']
        
        # Format the activities for JSON response
        activity_list = []
        for activity in activities:
            activity_list.append({
                "waste_id": activity.waste_item.waste_id,
                "status": activity.status,
                "user_name": activity.changed_by.get_full_name() or activity.changed_by.username,
                "timestamp": activity.timestamp.strftime("%b %d, %Y %H:%M")
            })
        
        return JsonResponse({
            "activities": activity_list,
            "counts": status_dict
        })
    else:
        # For non-factory users or admin - show all activities if they have permission
        if request.user.has_perm("inventory.can_view_analytics"):
            activities = (
                WasteHistory.objects.select_related("waste_item", "changed_by")
                .order_by("-timestamp")[:10]
            )
            
            # Get the updated status counts
            queryset = TextileWaste.objects.all()
            status_counts = queryset.values("status").annotate(count=Count("id"))
            
            # Convert status counts to a dictionary
            status_dict = {}
            for item in status_counts:
                status_dict[item['status']] = item['count']
            
            # Format the activities for JSON response
            activity_list = []
            for activity in activities:
                activity_list.append({
                    "waste_id": activity.waste_item.waste_id,
                    "status": activity.status,
                    "user_name": activity.changed_by.get_full_name() or activity.changed_by.username,
                    "timestamp": activity.timestamp.strftime("%b %d, %Y %H:%M")
                })
            
            return JsonResponse({
                "activities": activity_list,
                "counts": status_dict
            })
        else:
            # User doesn't have permission
            return JsonResponse({"activities": [], "error": "Permission denied"}, status=403)
