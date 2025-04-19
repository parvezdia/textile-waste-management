from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    # Dashboard as root URL
    path("", views.inventory_dashboard, name="dashboard"),
    # Waste Management
    path("waste/", views.waste_list, name="waste_list"),
    path("waste/upload/", views.upload_waste, name="upload_waste"),
    path("waste/<str:waste_id>/", views.waste_detail, name="waste_detail"),
    path("waste/<str:waste_id>/edit/", views.waste_edit, name="waste_edit"),
    path("waste/<str:waste_id>/delete/", views.waste_delete, name="waste_delete"),
    path("waste/<str:waste_id>/review/", views.review_waste, name="review_waste"),
    # New routes for approving and rejecting waste items
    path("waste/<str:waste_id>/approve/", views.approve_waste, name="approve_waste"),
    path("waste/<str:waste_id>/reject/", views.reject_waste, name="reject_waste"),
    # Reports and Analytics
    path("analytics/", views.inventory_analytics, name="analytics"),
    path("reports/", views.inventory_reports, name="reports"),
    # Removed the non-existent generate_report view
    path("reports/export/", views.export_report, name="export_report"),
    # Factory Views
    path("factory/inventory/", views.factory_inventory, name="factory_inventory"),
    path("factory/history/", views.factory_history, name="factory_history"),
    path("factory/reports/", views.factory_reports, name="factory_reports"),
    # API Endpoints for AJAX
    path("api/metrics/", views.get_metrics, name="api_metrics"),
    path("api/storage-efficiency/", views.get_storage_efficiency, name="api_storage_efficiency"),
    path("api/expiring-soon/", views.get_expiring_soon, name="api_expiring_soon"),
    path("api/impact-metrics/", views.get_impact_metrics, name="api_impact_metrics"),
    path("api/trend-metrics/", views.get_trend_metrics, name="api_trend_metrics"),
    path("api/activities/", views.get_recent_activities, name="api_activities"),  # New endpoint for recent activities
]
