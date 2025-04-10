from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("create/", views.create_order, name="create_order"),
    path("create/<str:design_id>/", views.create_order, name="create_order"),
    path("<str:order_id>/", views.order_detail, name="order_detail"),
    path(
        "<str:order_id>/update-status/",
        views.update_order_status,
        name="update_order_status",
    ),
    path("<str:order_id>/cancel/", views.cancel_order, name="cancel_order"),
]
