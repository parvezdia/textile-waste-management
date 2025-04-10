from django.db.models.signals import post_save
from django.dispatch import receiver

from transactions.models import Transaction

from .models import Order


@receiver(post_save, sender=Order)
def create_order_transaction(sender, instance, created, **kwargs):
    if created:
        # Create a new SALE transaction when order is created
        Transaction.objects.create(
            transaction_id=f"TXN-{instance.order_id}",
            order=instance,
            amount=instance.total_price,
            type="SALE",
            status="PENDING",
        )
    elif instance.status == "CANCELED":
        # Create a REFUND transaction if order is cancelled
        if instance.payment_info.status == "COMPLETED":
            Transaction.objects.create(
                transaction_id=f"REF-{instance.order_id}",
                order=instance,
                amount=instance.total_price,
                type="REFUND",
                status="PENDING",
            )
