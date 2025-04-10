from django.db import models


class PaymentInfo(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("CREDIT_CARD", "Credit Card"),
        ("BANK_TRANSFER", "Bank Transfer"),
        ("DIGITAL_WALLET", "Digital Wallet"),
        ("INVOICE", "Invoice"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("AUTHORIZED", "Authorized"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    payment_id = models.CharField(max_length=100, unique=True)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING"
    )
    transaction_date = models.DateTimeField(auto_now_add=True)

    def process_payment(self):
        # Payment processing logic to be implemented
        pass

    def refund_payment(self):
        # Refund processing logic to be implemented
        pass


class DeliveryInfo(models.Model):
    DELIVERY_STATUS_CHOICES = [
        ("PROCESSING", "Processing"),
        ("READY_FOR_PICKUP", "Ready for Pickup"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
        ("RETURNED", "Returned"),
    ]

    tracking_number = models.CharField(max_length=100, unique=True)
    carrier = models.CharField(max_length=100)
    address = models.TextField()
    estimated_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=DELIVERY_STATUS_CHOICES, default="PROCESSING"
    )

    def update_tracking_info(self, status):
        self.status = status
        self.save()

    def generate_label(self):
        # Shipping label generation logic to be implemented
        pass


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("IN_PRODUCTION", "In Production"),
        ("READY_FOR_DELIVERY", "Ready for Delivery"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("CANCELED", "Canceled"),
    ]

    order_id = models.CharField(max_length=100, unique=True)
    buyer = models.ForeignKey("accounts.Buyer", on_delete=models.CASCADE)
    design = models.ForeignKey("designs.Design", on_delete=models.CASCADE)
    customizations = models.JSONField(default=dict)  # Map of customization options
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default="PENDING"
    )
    date_ordered = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_info = models.OneToOneField(PaymentInfo, on_delete=models.CASCADE)
    delivery_info = models.OneToOneField(DeliveryInfo, on_delete=models.CASCADE)

    def calculate_total_price(self):
        base_price = self.design.price
        for option, choice in self.customizations.items():
            option_obj = self.design.customization_options.get(name=option)
            if option_obj:
                price_impact = option_obj.price_impact.get(choice, 0)
                base_price += price_impact
        return base_price

    def update_status(self, status):
        self.status = status
        self.save()
        from notifications.models import Notification

        Notification.objects.create(
            recipient=self.buyer.user,
            type="ORDER_UPDATE",
            message=f"Your order {self.order_id} status has been updated to {status}",
        )

    def generate_invoice(self):
        # Invoice generation logic to be implemented
        pass

    def cancel_order(self):
        if self.status not in ["DELIVERED", "SHIPPED"]:
            self.status = "CANCELED"
            self.save()
            from notifications.models import Notification

            Notification.objects.create(
                recipient=self.buyer.user,
                type="ORDER_UPDATE",
                message=f"Your order {self.order_id} has been cancelled",
            )
            return True
        return False

    def __str__(self):
        return f"Order {self.order_id} - {self.status}"

    class Meta:
        ordering = ["-date_ordered"]
