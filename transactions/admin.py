from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'type', 'amount', 'status', 'date')
    list_filter = ('type', 'status', 'date')
    search_fields = ('transaction_id', 'order__order_id')
    ordering = ('-date',)
