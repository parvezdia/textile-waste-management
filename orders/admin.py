from django.contrib import admin

from .models import DeliveryInfo, Order, PaymentInfo


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "buyer", "status", "total_price", "date_ordered")
    list_filter = ("status", "date_ordered")
    search_fields = ("order_id", "buyer__user__username")
    ordering = ("-date_ordered",)


@admin.register(PaymentInfo)
class PaymentInfoAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "method", "amount", "status", "transaction_date")
    list_filter = ("status", "method")
    search_fields = ("payment_id",)
    ordering = ("-transaction_date",)


@admin.register(DeliveryInfo)
class DeliveryInfoAdmin(admin.ModelAdmin):
    list_display = ("tracking_number", "carrier", "status", "estimated_delivery_date")
    list_filter = ("status", "carrier")
    search_fields = ("tracking_number",)
    ordering = ("-estimated_delivery_date",)
