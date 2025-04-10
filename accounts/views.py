from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import (
    BuyerForm,
    ContactInfoForm,
    DesignerForm,
    FactoryDetailsForm,
    LoginForm,
    UserRegistrationForm,
)
from .models import ContactInfo, FactoryDetails, FactoryPartner, User


def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Specify the backend explicitly
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Show appropriate message based on user type
            if user.user_type == "DESIGNER":
                messages.info(
                    request, 
                    'Your designer account has been created and is pending admin approval. '
                    'You will be prompted to complete your profile once approved.'
                )
                return redirect("designs:design_list")
            else:
                messages.success(request, "Registration successful! Please complete your profile.")

            return redirect("accounts:profile_setup")
    else:
        form = UserRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            try:
                user = User.objects.select_related(
                    "contact_info", "factorypartner", "factorypartner__factory_details",
                    "designer"
                ).get(email=email)

                if user.check_password(password):
                    login(
                        request,
                        user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )

                    # Check if designer is approved but profile incomplete
                    if user.user_type == "DESIGNER" and hasattr(user, "designer"):
                        designer = user.designer
                        contact_info = user.contact_info
                        
                        if not designer.is_approved:
                            messages.warning(
                                request,
                                "Your designer account is pending approval. "
                                "You will be notified once your account is approved.",
                            )
                            return redirect("designs:design_list")
                        elif not all([
                            contact_info and contact_info.address and contact_info.phone
                        ]):
                            messages.info(
                                request,
                                "Please complete your profile to start using your approved designer account.",
                            )
                            return redirect("accounts:profile_setup")
                        else:
                            return redirect("designs:designer_dashboard")

                    messages.success(request, "Login successful!")

                    # For factory users, check complete profile
                    if user.user_type == "FACTORY":
                        factory_partner = getattr(user, "factorypartner", None)
                        if factory_partner:
                            factory_details = factory_partner.factory_details
                            contact_info = user.contact_info

                            if (
                                factory_details
                                and factory_details.factory_name
                                and contact_info
                                and contact_info.address
                                and contact_info.phone
                            ):
                                return redirect("inventory:dashboard")

                        messages.warning(
                            request, "Please complete your factory profile setup."
                        )
                        return redirect("accounts:profile_setup")

                    # For buyers
                    elif user.user_type == "BUYER":
                        if hasattr(user, "buyer"):
                            return redirect("designs:design_list")
                        else:
                            return redirect("accounts:profile_setup")

                    return redirect("accounts:profile")
                else:
                    messages.error(request, "Invalid email or password")
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect("accounts:login")


@login_required
def profile(request):
    user = request.user
    try:
        # Check based on user type
        if user.user_type == "FACTORY":
            factory_partner = user.factorypartner
            factory_details = factory_partner.factory_details
            contact_info = user.contact_info

            # Ensure all required data exists
            if not all(
                [
                    factory_details and factory_details.factory_name,
                    contact_info and contact_info.address and contact_info.phone,
                ]
            ):
                messages.warning(request, "Please complete your factory profile setup")
                return redirect("accounts:profile_setup")

            profile_data = factory_partner

        elif user.user_type == "DESIGNER":
            profile_data = user.designer
        elif user.user_type == "BUYER":
            profile_data = user.buyer
        else:
            messages.warning(request, "Invalid user type")
            return redirect("accounts:profile_setup")

        if profile_data is None:
            raise ObjectDoesNotExist

    except (ObjectDoesNotExist, AttributeError):
        messages.warning(request, "Please complete your profile setup")
        return redirect("accounts:profile_setup")

    return render(
        request, "accounts/profile.html", {"user": user, "profile": profile_data}
    )


@login_required
def profile_setup(request):
    user = request.user

    # Check if profile is already complete for factory users
    if user.user_type == "FACTORY":
        try:
            factory_partner = user.factorypartner
            factory_details = factory_partner.factory_details
            contact_info = user.contact_info

            if all([
                factory_details and factory_details.factory_name,
                contact_info and contact_info.address and contact_info.phone
            ]):
                return redirect("inventory:dashboard")
        except (AttributeError, ObjectDoesNotExist):
            pass
    
    # Check if profile is complete for approved designers
    elif user.user_type == "DESIGNER" and hasattr(user, "designer"):
        designer = user.designer
        contact_info = user.contact_info
        if designer.is_approved and all([
            contact_info and contact_info.address and contact_info.phone
        ]):
            return redirect("designs:designer_dashboard")

    if request.method == "POST":
        contact_form = ContactInfoForm(request.POST, instance=user.contact_info)

        if user.user_type == "FACTORY":
            # Get or initialize contact info
            if not user.contact_info:
                contact_info = ContactInfo()
            else:
                contact_info = user.contact_info

            # Get or initialize factory partner and details
            try:
                factory_partner = user.factorypartner
                factory_details = factory_partner.factory_details
            except (AttributeError, ObjectDoesNotExist):
                factory_details = FactoryDetails()
                factory_partner = None

            factory_details_form = FactoryDetailsForm(
                request.POST, prefix="factory_details", instance=factory_details
            )

            if all([contact_form.is_valid(), factory_details_form.is_valid()]):
                try:
                    with transaction.atomic():
                        # Save contact info and link to user
                        contact_info = contact_form.save()
                        user.contact_info = contact_info
                        user.save()

                        # Save factory details
                        factory_details = factory_details_form.save()

                        # Create or update factory partner
                        if not factory_partner:
                            factory_partner = FactoryPartner.objects.create(
                                user=user, factory_details=factory_details
                            )
                        else:
                            factory_partner.factory_details = factory_details
                            factory_partner.save()

                    messages.success(request, "Factory profile updated successfully!")
                    return redirect("inventory:dashboard")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")
            else:
                if not contact_form.is_valid():
                    messages.error(
                        request,
                        "Please correct the errors in your contact information.",
                    )
                if not factory_details_form.is_valid():
                    messages.error(
                        request, "Please correct the errors in your factory details."
                    )

        elif user.user_type == "DESIGNER":
            profile_form = DesignerForm(request.POST, instance=user.designer)
            if contact_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        contact_form.save()
                        profile_form.save()
                        messages.success(request, "Designer profile updated successfully!")
                        return redirect("designs:designer_dashboard")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")

        elif user.user_type == "BUYER":
            profile_form = BuyerForm(request.POST, instance=user.buyer)
            if contact_form.is_valid() and profile_form.is_valid():
                try:
                    with transaction.atomic():
                        contact_form.save()
                        profile_form.save()
                        messages.success(request, "Buyer profile updated successfully!")
                        return redirect("designs:design_list")
                except Exception as e:
                    messages.error(request, f"Error saving profile: {str(e)}")
    else:
        contact_form = ContactInfoForm(instance=user.contact_info)

        if user.user_type == "FACTORY":
            try:
                factory_partner = user.factorypartner
                factory_details = factory_partner.factory_details
            except (AttributeError, ObjectDoesNotExist):
                factory_details = None

            factory_details_form = FactoryDetailsForm(
                prefix="factory_details", instance=factory_details
            )

            return render(
                request,
                "accounts/profile_setup.html",
                {
                    "contact_form": contact_form,
                    "factory_details_form": factory_details_form,
                    "user": user,
                },
            )
        elif user.user_type == "DESIGNER":
            profile_form = DesignerForm(instance=user.designer)
        elif user.user_type == "BUYER":
            profile_form = BuyerForm(instance=user.buyer)
        else:
            profile_form = None

    return render(
        request,
        "accounts/profile_setup.html",
        {"contact_form": contact_form, "profile_form": profile_form, "user": user},
    )
