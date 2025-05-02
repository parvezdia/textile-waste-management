from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve


class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_url = resolve(request.path_info).url_name
            user_type = request.user.user_type

            # Skip middleware for these paths
            skip_paths = [
                "profile",
                "profile_setup",
                "logout",
                "login",
                "register",
                "dashboard",
            ]
            if current_url in skip_paths:
                return self.get_response(request)

            # Role-based access rules
            allowed_urls = {
                "FACTORY": [
                    "dashboard",
                    "waste_list",
                    "waste_detail",
                    "upload_waste",
                    "factory_inventory",
                    "waste_edit",
                    "waste_delete",
                    "factory_history",
                    "factory_reports",
                ],
                "DESIGNER": [
                    "design_list", 
                    "design_detail", 
                    "design_create",
                    "designer_dashboard",
                    "customization_option_create",
                    "image_upload"
                ],
                "BUYER": [
                    "design_list", 
                    "design_detail", 
                    "order_create", 
                    "order_list"
                ],
            }

            # Check if URL is allowed for user type
            if current_url not in allowed_urls.get(user_type, []):
                messages.warning(
                    request,
                    f"Access denied. This page is not accessible for {user_type.lower()} users.",
                )

                # Redirect based on user type
                if user_type == "FACTORY":
                    if hasattr(request.user, "factorypartner"):
                        return redirect("inventory:dashboard")
                    else:
                        messages.warning(
                            request, "Please complete your factory profile setup."
                        )
                        return redirect("accounts:profile_setup")
                elif user_type == "DESIGNER":
                    # Check if designer is approved and has complete profile
                    if hasattr(request.user, "designer"):
                        designer = request.user.designer
                        contact_info = request.user.contact_info
                        
                        if not designer.is_approved:
                            messages.warning(
                                request,
                                "Your designer account is pending approval."
                            )
                            return redirect("designs:design_list")
                        elif not all([
                            contact_info and contact_info.address and contact_info.phone
                        ]):
                            messages.info(
                                request,
                                "Please complete your profile to access the designer dashboard."
                            )
                            return redirect("accounts:profile_setup")
                        else:
                            return redirect("designs:designer_dashboard")
                    else:
                        return redirect("accounts:profile_setup")
                elif user_type == "BUYER":
                    return redirect("designs:design_list")

        return self.get_response(request)


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Exempt these paths from redirect
            exempt_paths = [
                "/accounts/profile-setup/",
                "/accounts/logout/",
                "/static/",
                "/media/",
            ]

            # Allow profile-setup with ?edit=true
            if request.path.startswith("/accounts/profile-setup/") and request.GET.get("edit") == "true":
                return self.get_response(request)

            # Check if current path is exempt
            current_path = request.path
            if not any(current_path.startswith(path) for path in exempt_paths):
                # Check profile completion based on user type
                if request.user.user_type == "FACTORY":
                    if hasattr(request.user, "factorypartner"):
                        factory_details = request.user.factorypartner.factory_details
                        contact_info = request.user.contact_info

                        if not all(
                            [
                                factory_details and factory_details.factory_name,
                                contact_info
                                and contact_info.address
                                and contact_info.phone,
                            ]
                        ):
                            return redirect("accounts:profile_setup")
                    else:
                        return redirect("accounts:profile_setup")

                elif request.user.user_type == "DESIGNER":
                    if hasattr(request.user, "designer"):
                        designer = request.user.designer
                        contact_info = request.user.contact_info
                        
                        # If designer is approved but profile is incomplete
                        if designer.is_approved and not all([
                            contact_info and contact_info.address and contact_info.phone
                        ]):
                            return redirect("accounts:profile_setup")
                    else:
                        return redirect("accounts:profile_setup")

                elif request.user.user_type == "BUYER":
                    if not hasattr(request.user, "buyer"):
                        return redirect("accounts:profile_setup")

        response = self.get_response(request)
        return response
