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
]
