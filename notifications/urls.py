from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('count/', views.notification_count, name='notification_count'),
    path('unread-count/', views.notification_count, name='unread_count'),  # Added alias endpoint for JavaScript
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]
