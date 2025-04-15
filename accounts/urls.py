from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/setup/", views.profile_setup, name="profile_setup"),
    path("designer/<int:designer_id>/", views.designer_profile, name="designer_profile"),
    
    # Admin dashboard and related URLs
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/factory-waste/", views.admin_factory_waste, name="admin_factory_waste"),
    path("admin/approve-waste/<int:waste_id>/", views.admin_approve_waste, name="admin_approve_waste"),
    path("admin/reject-waste/<int:waste_id>/", views.admin_reject_waste, name="admin_reject_waste"),
    path("admin/designers/", views.admin_designers, name="admin_designers"),
    path("admin/approve-designer/<int:designer_id>/", views.admin_approve_designer, name="admin_approve_designer"),
    path("admin/designer/<int:designer_id>/designs/", views.admin_designer_designs, name="admin_designer_designs"),
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("admin/update-order-status/<int:order_id>/", views.admin_update_order_status, name="admin_update_order_status"),
    path("admin/approve-payment/<int:order_id>/", views.admin_approve_payment, name="admin_approve_payment"),
    path("admin/analytics/", views.admin_analytics, name="admin_analytics"),
    path("admin/sustainability/", views.admin_sustainability, name="admin_sustainability"),
    path("admin/generate-sustainability-report/", views.generate_sustainability_report, name="generate_sustainability_report"),
]
