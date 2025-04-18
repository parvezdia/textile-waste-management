import uuid
from django.utils import timezone
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification


def generate_notification_id():
    """Generate a unique notification ID"""
    return f"NTF-{uuid.uuid4().hex[:8].upper()}"


def send_notification(user, message, notification_type='info'):
    """
    Send a notification to a specific user through WebSocket and save to database.
    
    Args:
        user: The user to send the notification to
        message: The notification message
        notification_type: Type of notification (info, success, warning, error)
    """
    notification = Notification.objects.create(
        user=user,
        message=message,
        notification_type=notification_type
    )
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}_notifications",
        {
            "type": "notification_message",
            "message": {
                "notification_type": notification_type,
                "message": message,
                "notification_id": notification.id
            }
        }
    )
    
    return notification


def get_user_notifications(user, include_read=False, limit=None):
    """Get notifications for a user"""
    notifications = Notification.objects.filter(user=user)
    if not include_read:
        notifications = notifications.filter(is_read=False)
    if limit:
        notifications = notifications[:limit]
    return notifications.order_by("-created_at")


def mark_notifications_as_read(user, notification_ids=None):
    """Mark notifications as read"""
    notifications = Notification.objects.filter(user=user)
    if notification_ids:
        notifications = notifications.filter(id__in=notification_ids)
    notifications.update(is_read=True)
    return notifications.count()


def get_notification_stats(user):
    """Get notification statistics for a user"""
    all_notifications = Notification.objects.filter(user=user)
    return {
        "total": all_notifications.count(),
        "unread": all_notifications.filter(is_read=False).count(),
        "types": all_notifications.values("notification_type").annotate(count=models.Count("id")),
        "latest": all_notifications.order_by("-created_at").first(),
    }


def clean_old_notifications(days=30):
    """Remove notifications older than specified days"""
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    return Notification.objects.filter(
        created_at__lt=cutoff_date, is_read=True
    ).delete()


def bulk_create_notifications(notifications_data):
    """Bulk create notifications"""
    notifications = [
        Notification(
            user=data["user"],
            notification_type=data["notification_type"],
            message=data["message"],
        )
        for data in notifications_data
    ]
    return Notification.objects.bulk_create(notifications)


def send_bulk_notification(users, message, notification_type='info'):
    """Send the same notification to multiple users."""
    notifications = []
    channel_layer = get_channel_layer()
    
    for user in users:
        # Create notification record
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            message=message
        )
        notifications.append(notification)
        
        # Send real-time notification
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}_notifications",
            {
                "type": "notification_message",
                "message": {
                    "notification_type": notification_type,
                    "message": message,
                    "notification_id": notification.id
                }
            }
        )
    
    return notifications
