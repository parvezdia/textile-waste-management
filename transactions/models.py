from django.db import models

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('SALE', 'Sale'),
        ('REFUND', 'Refund'),
        ('FEE', 'Fee'),
        ('COMMISSION', 'Commission'),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    transaction_id = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='PENDING')

    def generate_receipt(self):
        # Receipt generation logic
        pass

    def __str__(self):
        return f"{self.transaction_id} - {self.type} ({self.status})"

    class Meta:
        ordering = ['-date']
