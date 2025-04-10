from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from notifications.utils import send_notification

from .models import Buyer, ContactInfo, Designer, FactoryDetails, FactoryPartner, User


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "user_type", "is_active", "date_joined")
    list_filter = ("user_type", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)


@admin.register(Designer)
class DesignerAdmin(admin.ModelAdmin):
    list_display = ("user", "is_approved", "approval_date")
    list_filter = ("is_approved",)
    search_fields = ("user__username", "user__email")
    actions = ["approve_designers"]

    def approve_designers(self, request, queryset):
        for designer in queryset:
            if not designer.is_approved:
                designer.is_approved = True
                designer.approval_date = timezone.now()
                designer.save()

                # Send notification to the designer with updated message
                send_notification(
                    recipient=designer.user,
                    notification_type="SYSTEM_NOTIFICATION",
                    message="Congratulations! Your designer account has been approved. Please complete your profile setup to start creating designs.",
                )

        self.message_user(
            request, f"{queryset.count()} designer(s) were successfully approved."
        )

    approve_designers.short_description = "Approve selected designers"


@admin.register(FactoryPartner)
class FactoryPartnerAdmin(admin.ModelAdmin):
    list_display = ("user", "factory_details")
    search_fields = ("user__username", "factory_details__factory_name")


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username", "user__email")


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("address", "phone", "alternate_email")
    search_fields = ("address", "phone", "alternate_email")


@admin.register(FactoryDetails)
class FactoryDetailsAdmin(admin.ModelAdmin):
    list_display = ("factory_name", "location", "production_capacity")
    search_fields = ("factory_name", "location")
    list_filter = ("certifications",)


admin.site.register(User, CustomUserAdmin)
