from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-date_created"
    )
    unread_count = notifications.filter(is_read=False).count()
    return render(
        request,
        "notifications/notification_list.html",
        {"notifications": notifications, "unread_count": unread_count},
    )


@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification, notification_id=notification_id, recipient=request.user
    )
    notification.mark_as_read()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    return redirect("notifications:notification_list")


@login_required
def mark_all_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True
    )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    return redirect("notifications:notification_list")


@login_required
def notification_count(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"count": count})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(notification_id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user).update(is_read=True)
    return JsonResponse({'status': 'success'})
