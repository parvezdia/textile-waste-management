from django.db import models
from django.conf import settings

class LegacyNotification(models.Model):
    # This class represents the notifications_legacynotification table in your database
    class Meta:
        db_table = 'notifications_legacynotification'
        managed = False  # Tells Django not to manage this model with migrations


class UserNotification(models.Model):
    # This class represents the notifications_usernotification table in your database
    class Meta:
        db_table = 'notifications_usernotification'
        managed = False  # Tells Django not to manage this model with migrations


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('waste_approved', 'Waste Approved'),
        ('waste_rejected', 'Waste Rejected'),
        ('order_status_update', 'Order Status Update'),
        ('payment_approved', 'Payment Approved'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"

    def mark_as_read(self):
        self.is_read = True
        self.save()
