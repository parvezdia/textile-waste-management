from django.urls import path

from . import views

app_name = "designs"

urlpatterns = [
    path("", views.design_list, name="design_list"),
    path("dashboard/", views.designer_dashboard, name="designer_dashboard"),
    path("create/", views.design_create, name="design_create"),
    path("<str:design_id>/", views.design_detail, name="design_detail"),
    path("<str:design_id>/edit/", views.design_edit, name="design_edit"),
    path("<str:design_id>/delete/", views.design_delete, name="design_delete"),
]
