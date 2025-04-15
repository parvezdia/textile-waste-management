import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    Admin,
    AdminLevel,
    Buyer,
    BuyerPreferences,
    ContactInfo,
    Designer,
    FactoryDetails,
    FactoryPartner,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile and related models on user creation"""
    if created:
        with transaction.atomic():
            # Always create contact info
            if not hasattr(instance, "contact_info") or instance.contact_info is None:
                contact_info = ContactInfo.objects.create()
                instance.contact_info = contact_info
                instance.save()

            # For superusers created via createsuperuser, set user_type to ADMIN
            if instance.is_superuser and not instance.user_type:
                instance.user_type = "ADMIN"
                instance.save(update_fields=['user_type'])
                
            # Create role-specific profile based on user_type
            if instance.user_type == "FACTORY":
                if not hasattr(instance, "factorypartner"):
                    factory_details = FactoryDetails.objects.create()
                    FactoryPartner.objects.create(
                        user=instance, factory_details=factory_details
                    )
            elif instance.user_type == "DESIGNER":
                if not hasattr(instance, "designer"):
                    # Create designer with unapproved status
                    Designer.objects.create(
                        user=instance, is_approved=False, approval_date=None
                    )
            elif instance.user_type == "BUYER":
                if not hasattr(instance, "buyer"):
                    preferences = BuyerPreferences.objects.create()
                    Buyer.objects.create(user=instance, preferences=preferences)
            elif instance.user_type == "ADMIN":
                if not hasattr(instance, "admin"):
                    Admin.objects.create(
                        user=instance,
                        admin_level=AdminLevel.SUPER_ADMIN if instance.is_superuser else AdminLevel.JUNIOR
                    )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save related profile models when user is saved"""
    with transaction.atomic():
        # Ensure contact_info exists and is saved
        if hasattr(instance, "contact_info"):
            instance.contact_info.save()

        # Save existing profile if it exists
        if hasattr(instance, "factory_partner"):
            instance.factory_partner.save()
        elif hasattr(instance, "designer"):
            instance.designer.save()
        elif hasattr(instance, "buyer"):
            instance.buyer.save()
        elif hasattr(instance, "admin"):
            instance.admin.save()


@receiver(post_save, sender=ContactInfo)
def update_related_models(sender, instance, **kwargs):
    """Update related models when contact info is updated"""
    try:
        if hasattr(instance, "factorypartner"):
            instance.factorypartner.save()
    except Exception as e:
        logger.error(f"Error updating related models: {str(e)}")
