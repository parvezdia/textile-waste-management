from datetime import timedelta
from io import BytesIO

import pandas as pd
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from reportlab.pdfgen import canvas

from .models import TextileWaste


def get_available_waste_stats():
    """Get statistics about available textile waste"""
    available_waste = TextileWaste.objects.filter(status="AVAILABLE")
    return {
        "total_count": available_waste.count(),
        "total_quantity": available_waste.aggregate(Sum("quantity"))["quantity__sum"]
        or 0,
        "by_material": available_waste.values("material").annotate(
            total=Sum("quantity"), items=Count("id")
        ),
        "by_type": available_waste.values("type").annotate(
            total=Sum("quantity"), items=Count("id")
        ),
    }


def check_waste_availability(waste_id, required_quantity):
    """Check if requested quantity of waste is available"""
    try:
        waste = TextileWaste.objects.get(waste_id=waste_id, status="AVAILABLE")
        if not waste.factory.factory_details.has_available_capacity():
            return False
        return waste.quantity >= required_quantity
    except TextileWaste.DoesNotExist:
        return False


def reserve_waste(waste_id, quantity):
    """Reserve a specific quantity of waste for an order"""
    try:
        waste = TextileWaste.objects.get(waste_id=waste_id, status="AVAILABLE")
        factory = waste.factory

        # Check factory capacity
        if not factory.factory_details.has_available_capacity():
            return False

        if waste.quantity >= quantity:
            # Create new waste entry for reserved portion
            reserved_waste = TextileWaste.objects.create(
                waste_id=f"{waste_id}_R{timezone.now().strftime('%Y%m%d%H%M')}",
                type=waste.type,
                material=waste.material,
                quantity=quantity,
                unit=waste.unit,
                color=waste.color,
                dimensions=waste.dimensions,
                quality_grade=waste.quality_grade,
                factory=factory,
                status="RESERVED",
            )

            # Update original waste quantity
            waste.quantity -= quantity
            if waste.quantity == 0:
                waste.status = "USED"
            waste.save()

            return True
    except TextileWaste.DoesNotExist:
        pass
    return False


def calculate_storage_efficiency(factory=None):
    """Calculate storage efficiency metrics"""
    queryset = TextileWaste.objects.filter(status__in=["AVAILABLE", "RESERVED"])
    if factory:
        queryset = queryset.filter(factory=factory)
        capacity = factory.factory_details.production_capacity
    else:
        capacity = 1000  # Default capacity for general calculations

    if not queryset.exists():
        return {
            "storage_utilization": 0,
            "avg_days_in_storage": 0,
            "turnover_rate": 0,
            "capacity_breakdown": {},
        }

    current_usage = sum(item.quantity for item in queryset)
    storage_utilization = (current_usage / capacity) * 100 if capacity else 0

    # Calculate average days in storage
    now = timezone.now()
    total_days = sum((now - item.date_added).days for item in queryset)
    avg_days = total_days / queryset.count() if queryset.count() > 0 else 0

    # Calculate turnover rate - improved calculation
    thirty_days_ago = now - timedelta(days=30)
    
    # Get items that were marked as USED in the last 30 days
    used_items_query = TextileWaste.objects.filter(
        status="USED", 
        last_updated__gte=thirty_days_ago
    )
    
    # Add factory filter if provided
    if factory:
        used_items_query = used_items_query.filter(factory=factory)
    
    # Count the items and their total quantity
    used_items_count = used_items_query.count()
    used_items_quantity = used_items_query.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Calculate available items
    available_count = queryset.count()
    available_quantity = current_usage
    
    # Calculate turnover rate based on both count and quantity
    total_items = available_count + used_items_count
    total_quantity = available_quantity + used_items_quantity
    
    # Use quantity-based turnover if available, otherwise fallback to count-based
    if total_quantity > 0:
        turnover_rate = (used_items_quantity / total_quantity * 100)
    elif total_items > 0:
        turnover_rate = (used_items_count / total_items * 100)
    else:
        turnover_rate = 0
    
    # Get capacity breakdown
    capacity_breakdown = {}
    if factory:
        capacity_breakdown = factory.factory_details.get_capacity_breakdown()

    return {
        "storage_utilization": min(100, storage_utilization),
        "avg_days_in_storage": avg_days,
        "turnover_rate": turnover_rate,
        "capacity_breakdown": capacity_breakdown,
    }


def get_inventory_metrics(factory=None):
    """Get key metrics for inventory dashboard"""
    base_query = TextileWaste.objects
    if factory:
        base_query = base_query.filter(factory=factory)

    # Calculate metrics
    metrics = {
        "total_items": base_query.count(),
        "total_quantity": base_query.aggregate(total=Sum("quantity"))["total"] or 0,
        "pending_review": base_query.filter(status="PENDING_REVIEW").count(),
        "efficiency": calculate_storage_efficiency(factory),
    }
    
    # Calculate average sustainability score directly
    sustainability_data = base_query.aggregate(
        avg=Avg("sustainability_score")
    )
    
    avg_sustainability = sustainability_data["avg"] or 0
    
    # Convert from 0-100 scale to 0-10 scale for display
    metrics["avg_sustainability"] = avg_sustainability / 10
    
    # Add capacity recommendation if factory specified
    if factory:
        recommended = factory.factory_details.calculate_recommended_capacity()
        if recommended:
            metrics["recommended_capacity"] = recommended

    return metrics


def get_expiring_inventory(days=30, factory=None):
    """Get inventory items that will expire soon"""
    queryset = TextileWaste.objects.filter(
        status="AVAILABLE",
        expiry_date__isnull=False,
        expiry_date__gt=timezone.now(),
        expiry_date__lte=timezone.now() + timedelta(days=days),
    )

    if factory:
        queryset = queryset.filter(factory=factory)

    return queryset.order_by("expiry_date")


def generate_waste_report(start_date, end_date, factory=None):
    """Generate a comprehensive waste report for the given period"""
    queryset = TextileWaste.objects.filter(date_added__range=[start_date, end_date])
    if factory:
        queryset = queryset.filter(factory=factory)

    # Material breakdown as a list of dicts for template rendering
    material_breakdown = []
    for entry in queryset.values("material").annotate(
        quantity=Sum("quantity"),
        items=Count("id"),
        avg_score=Avg("sustainability_score")
    ):
        material_breakdown.append({
            "name": entry["material"],
            "quantity": entry["quantity"],
            "items": entry["items"],
            "avg_score": entry["avg_score"],
        })

    report = {
        "period": {"start": start_date, "end": end_date},
        "total_items": queryset.count(),
        "total_quantity": queryset.aggregate(total=Sum("quantity"))["total"] or 0,
        "total_weight": queryset.aggregate(total=Sum("quantity"))["total"] or 0,  # For compatibility
        "avg_daily_intake": queryset.values("date_added__date")
            .annotate(daily_total=Sum("quantity"))
            .aggregate(Avg("daily_total"))["daily_total__avg"] or 0,
        "status_breakdown": list(queryset.values("status").annotate(
            count=Count("id"), quantity=Sum("quantity")
        )),
        "material_breakdown": material_breakdown,
        "quality_breakdown": list(queryset.values("quality_grade").annotate(
            count=Count("id"), quantity=Sum("quantity")
        )),
        "sustainability_metrics": {
            "average_score": queryset.aggregate(avg=Avg("sustainability_score"))["avg"] or 0,
            "high_impact": queryset.filter(sustainability_score__gte=80).count(),
            "medium_impact": queryset.filter(sustainability_score__range=[50, 79]).count(),
            "low_impact": queryset.filter(sustainability_score__lt=50).count(),
        },
        "items": queryset,
        "waste_by_type": list(queryset.values("type").annotate(total=Sum("quantity"))),
    }

    return report


def get_similar_waste_items(waste_item, limit=5):
    """Find similar waste items based on material and type"""
    return (
        TextileWaste.objects.filter(
            status="AVAILABLE", material=waste_item.material, type=waste_item.type
        )
        .exclude(id=waste_item.id)
        .order_by("-sustainability_score")[:limit]
    )


def export_report_as_pdf(report_data):
    """Export inventory report as PDF"""
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontSize=24, spaceAfter=30
    )
    elements.append(Paragraph("Inventory Report", title_style))
    elements.append(Spacer(1, 20))

    # Period
    period = f"Period: {report_data['period']['start'].strftime('%B %d, %Y')} - {report_data['period']['end'].strftime('%B %d, %Y')}"
    elements.append(Paragraph(period, styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Summary Statistics
    data = [
        ["Metric", "Value"],
        ["Total Items", str(report_data["total_items"])],
        ["Total Quantity", f"{report_data['total_quantity']:.2f} kg"],
        [
            "Average Sustainability Score",
            f"{report_data['sustainability_metrics']['average_score']:.1f}",
        ],
    ]

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def make_timezone_naive(data):
    """Convert all timezone-aware datetime objects in a complex data structure to naive datetime objects"""
    import copy
    import datetime

    # Make a deep copy to avoid modifying the original data
    result = copy.deepcopy(data)

    if isinstance(result, dict):
        for key, value in result.items():
            if hasattr(value, "tzinfo") and value.tzinfo is not None:
                result[key] = value.replace(tzinfo=None)
            elif isinstance(value, (dict, list)):
                result[key] = make_timezone_naive(value)
    elif isinstance(result, list):
        for i, item in enumerate(result):
            if hasattr(item, "tzinfo") and item.tzinfo is not None:
                result[i] = item.replace(tzinfo=None)
            elif isinstance(item, (dict, list)):
                result[i] = make_timezone_naive(item)

    return result


def export_report_as_excel(report_data):
    """Generate Excel report"""
    from io import BytesIO
    import pandas as pd
    import copy
    import datetime

    # Create Excel writer
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Summary sheet
        summary_data = {
            "Metric": ["Total Items", "Total Weight (kg)", "Avg Daily Intake (kg)"],
            "Value": [
                report_data["total_items"],
                report_data["total_weight"],
                report_data["avg_daily_intake"],
            ],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # Environmental Impact sheet
        impact = report_data["environmental_impact"]
        impact_data = {
            "Metric": [
                "CO2 Saved (kg)",
                "Water Saved (L)",
                "Landfill Space Reduced (m³)",
            ],
            "Value": [
                impact["co2_saved"],
                impact["water_saved"],
                impact["landfill_reduced"],
            ],
        }
        pd.DataFrame(impact_data).to_excel(
            writer, sheet_name="Environmental Impact", index=False
        )

        # Status breakdown sheet
        if "status_breakdown" in report_data:
            # Convert QuerySet to list of dicts and handle datetime objects
            status_data = []
            for item in report_data["status_breakdown"]:
                row = {}
                for key, value in item.items():
                    if isinstance(value, datetime.datetime) and value.tzinfo is not None:
                        row[key] = value.replace(tzinfo=None)
                    else:
                        row[key] = value
                status_data.append(row)
            
            status_df = pd.DataFrame(status_data)
            status_df.to_excel(writer, sheet_name="Status Breakdown", index=False)

        # Material breakdown sheet
        if "material_breakdown" in report_data:
            # Convert QuerySet to list of dicts and handle datetime objects
            material_data = []
            for item in report_data["material_breakdown"]:
                row = {}
                for key, value in item.items():
                    if isinstance(value, datetime.datetime) and value.tzinfo is not None:
                        row[key] = value.replace(tzinfo=None)
                    else:
                        row[key] = value
                material_data.append(row)
                
            material_df = pd.DataFrame(material_data)
            material_df.to_excel(writer, sheet_name="Material Breakdown", index=False)

        # Quality breakdown sheet
        if "quality_breakdown" in report_data:
            # Convert QuerySet to list of dicts and handle datetime objects
            quality_data = []
            for item in report_data["quality_breakdown"]:
                row = {}
                for key, value in item.items():
                    if isinstance(value, datetime.datetime) and value.tzinfo is not None:
                        row[key] = value.replace(tzinfo=None)
                    else:
                        row[key] = value
                quality_data.append(row)
                
            quality_df = pd.DataFrame(quality_data)
            quality_df.to_excel(writer, sheet_name="Quality Analysis", index=False)

        # Format workbook - using a simpler approach
        # Just set column width and freeze the headers
        for sheet in writer.sheets:
            worksheet = writer.sheets[sheet]
            worksheet.set_column(0, 20, 15)  # Set width for all columns
            worksheet.freeze_panes(1, 0)  # Freeze the first row

    return output.getvalue()


def calculate_sustainability_impact(report_data):
    """Calculate environmental impact metrics based on waste management"""
    total_quantity = report_data["total_quantity"]
    avg_sustainability = report_data["sustainability_metrics"]["average_score"]

    # Calculate CO2 emissions saved (rough estimate)
    # Assuming 1 kg of reused textile waste saves about 3.6 kg of CO2
    co2_saved = total_quantity * 3.6

    # Calculate water saved (rough estimate)
    # Assuming 1 kg of reused textile saves about 2000 liters of water
    water_saved = total_quantity * 2000

    # Calculate landfill space saved (rough estimate)
    # Assuming 1 kg of textile takes about 0.01 cubic meters in landfill
    landfill_saved = total_quantity * 0.01

    return {
        "co2_saved": co2_saved,
        "water_saved": water_saved,
        "landfill_saved": landfill_saved,
        "sustainability_score": avg_sustainability,
        "impact_category": "High"
        if avg_sustainability >= 80
        else "Medium"
        if avg_sustainability >= 50
        else "Low",
    }


def get_trends_analysis(start_date, end_date, factory=None):
    """Analyze trends in waste management over time"""
    from django.db.models import Avg, Count
    from django.db.models.functions import TruncWeek

    from .models import TextileWaste

    queryset = TextileWaste.objects.filter(date_added__range=[start_date, end_date])

    if factory:
        queryset = queryset.filter(factory=factory)

    weekly_trends = (
        queryset.annotate(week=TruncWeek("date_added"))
        .values("week")
        .annotate(
            items_count=Count("id"), avg_sustainability=Avg("sustainability_score")
        )
        .order_by("week")
    )

    material_trends = (
        queryset.values("material")
        .annotate(
            total_items=Count("id"), avg_sustainability=Avg("sustainability_score")
        )
        .order_by("-total_items")
    )

    quality_trends = (
        queryset.values("quality_grade")
        .annotate(
            total_items=Count("id"), avg_sustainability=Avg("sustainability_score")
        )
        .order_by("quality_grade")
    )

    return {
        "weekly_trends": list(weekly_trends),
        "material_trends": list(material_trends),
        "quality_trends": list(quality_trends),
    }


def calculate_sustainability_impact(report_data):
    """Calculate environmental impact metrics"""
    total_weight = report_data["total_weight"]

    return {
        "co2_saved": round(total_weight * 2.89, 2),  # kg CO2 saved (EPA estimate)
        "water_saved": round(total_weight * 2700, 2),  # liters of water saved
        "landfill_reduced": round(total_weight * 0.82, 2),  # cubic meters saved
    }


def export_report_as_pdf(report_data):
    """Generate PDF report"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Add report title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, "Textile Waste Inventory Report")

    # Add summary statistics
    p.setFont("Helvetica", 12)
    y = 750
    p.drawString(50, y, f"Total Items: {report_data['total_items']}")
    p.drawString(50, y - 20, f"Total Weight: {report_data['total_weight']} kg")
    p.drawString(
        50, y - 40, f"Average Daily Intake: {report_data['avg_daily_intake']:.2f} kg"
    )

    # Add environmental impact
    y = 650
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Environmental Impact")
    p.setFont("Helvetica", 12)
    impact = report_data["environmental_impact"]
    p.drawString(50, y - 30, f"CO2 Saved: {impact['co2_saved']} kg")
    p.drawString(50, y - 50, f"Water Saved: {impact['water_saved']} L")
    p.drawString(50, y - 70, f"Landfill Space Reduced: {impact['landfill_reduced']} m³")

    p.save()
    return buffer.getvalue()

