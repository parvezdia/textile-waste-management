from django.contrib import admin
from django.utils.html import format_html

from .models import Dimensions, TextileWaste, WasteHistory


class WasteHistoryInline(admin.TabularInline):
    model = WasteHistory
    extra = 0
    readonly_fields = ("timestamp", "changed_by", "status", "notes")
    can_delete = False
    max_num = 0


@admin.register(TextileWaste)
class TextileWasteAdmin(admin.ModelAdmin):
    list_display = (
        "waste_id",
        "type",
        "material",
        "quantity_with_unit",
        "status_badge",
        "factory",
        "sustainability_score",
        "date_added",
    )
    list_filter = ("status", "type", "material", "quality_grade", "factory")
    search_fields = ("waste_id", "type", "material", "factory__name", "description")
    readonly_fields = ("waste_id", "date_added", "last_updated", "sustainability_score")
    ordering = ("-date_added",)
    inlines = [WasteHistoryInline]

    def quantity_with_unit(self, obj):
        return f"{obj.quantity} {obj.unit}"

    quantity_with_unit.short_description = "Quantity"

    def status_badge(self, obj):
        colors = {
            "AVAILABLE": "success",
            "RESERVED": "info",
            "USED": "secondary",
            "EXPIRED": "danger",
            "PENDING_REVIEW": "warning",
        }
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            colors.get(obj.status, "primary"),
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("factory", "dimensions")

    class Media:
        css = {
            "all": [
                "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"
            ]
        }


@admin.register(Dimensions)
class DimensionsAdmin(admin.ModelAdmin):
    list_display = ("id", "dimensions_display", "unit", "waste_item")
    list_filter = ("unit",)
    search_fields = ("waste_item__waste_id",)

    def dimensions_display(self, obj):
        return f"{obj.length} × {obj.width}"

    dimensions_display.short_description = "Dimensions"

    def waste_item(self, obj):
        try:
            waste = obj.textilewaste
            return format_html(
                '<a href="{}">{}</a>',
                f"/admin/inventory/textilewaste/{waste.id}/change/",
                waste.waste_id,
            )
        except TextileWaste.DoesNotExist:
            return "-"

    waste_item.short_description = "Associated Waste"


@admin.register(WasteHistory)
class WasteHistoryAdmin(admin.ModelAdmin):
    list_display = ("waste_item", "status", "changed_by", "timestamp")
    list_filter = ("status", "timestamp", "changed_by")
    search_fields = ("waste_item__waste_id", "notes")
    readonly_fields = ("waste_item", "status", "changed_by", "timestamp")
    ordering = ("-timestamp",)
