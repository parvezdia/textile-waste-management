from django.contrib import admin

from .models import CustomizationOption, Design, Image


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("design_id", "name", "designer", "price", "status", "date_created")
    list_filter = ("status", "date_created")
    search_fields = ("design_id", "name", "designer__user__username")
    ordering = ("-date_created",)


@admin.register(CustomizationOption)
class CustomizationOptionAdmin(admin.ModelAdmin):
    list_display = ("option_id", "name", "type")
    list_filter = ("type",)
    search_fields = ("name", "option_id")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("image_id", "filename", "upload_date")
    search_fields = ("image_id", "filename")
    ordering = ("-upload_date",)
