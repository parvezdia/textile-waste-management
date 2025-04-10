import uuid

from django.db.models import Avg, Count

from .models import Design


def generate_design_id():
    """Generate a unique design ID"""
    return f"DSG-{uuid.uuid4().hex[:8].upper()}"


def get_designer_statistics(designer):
    """Get statistics about a designer's portfolio"""
    designs = Design.objects.filter(designer=designer)
    return {
        "total_designs": designs.count(),
        "published_designs": designs.filter(status="PUBLISHED").count(),
        "average_price": designs.filter(status="PUBLISHED").aggregate(Avg("price"))[
            "price__avg"
        ]
        or 0,
        "designs_by_material": designs.values("required_materials__material").annotate(
            count=Count("id")
        ),
        "customizable_designs": designs.filter(customization_options__isnull=False)
        .distinct()
        .count(),
    }


def check_material_requirements(design_id):
    """Check if all required materials for a design are available"""
    try:
        design = Design.objects.get(design_id=design_id)
        for material in design.required_materials.all():
            if material.status != "AVAILABLE" or material.quantity <= 0:
                return False
        return True
    except Design.DoesNotExist:
        return False


def calculate_customization_price(design_id, customizations):
    """Calculate total price including customizations"""
    try:
        design = Design.objects.get(design_id=design_id)
        total_price = design.price

        for option, choice in customizations.items():
            option_obj = design.customization_options.get(name=option)
            if option_obj and choice in option_obj.price_impact:
                total_price += option_obj.price_impact[choice]

        return total_price
    except Design.DoesNotExist:
        return None
    except Exception:
        return None
