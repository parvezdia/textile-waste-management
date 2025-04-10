from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class ContactInfo(models.Model):
    address = models.TextField()
    phone = models.CharField(max_length=20)
    alternate_email = models.EmailField(blank=True, null=True)


class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ("FACTORY", "Factory Partner"),
        ("DESIGNER", "Designer"),
        ("BUYER", "Buyer"),
    ]

    email = models.EmailField(unique=True)
    contact_info = models.OneToOneField(
        ContactInfo, on_delete=models.CASCADE, null=True
    )
    date_registered = models.DateTimeField(default=timezone.now)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    def update_profile(self, info):
        if self.contact_info:
            self.contact_info.address = info.get("address", self.contact_info.address)
            self.contact_info.phone = info.get("phone", self.contact_info.phone)
            self.contact_info.alternate_email = info.get(
                "alternate_email", self.contact_info.alternate_email
            )
            self.contact_info.save()


class FactoryDetails(models.Model):
    CERTIFICATION_TYPES = [
        "ISO9001",
        "ISO14001",
        "SA8000",
        "GOTS",
        "OEKO-TEX",
        "WRAP",
        "GRS",
    ]

    factory_name = models.CharField(max_length=200, blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    certifications = models.JSONField(default=list)
    production_capacity = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.factory_name or "Unnamed Factory"

    def add_certification(self, cert_type):
        if (
            cert_type in self.CERTIFICATION_TYPES
            and cert_type not in self.certifications
        ):
            self.certifications.append(cert_type)
            self.save()
            return True
        return False

    def remove_certification(self, cert_type):
        if cert_type in self.certifications:
            self.certifications.remove(cert_type)
            self.save()
            return True
        return False

    def get_current_capacity_usage(self):
        """Get current capacity usage from waste inventory"""
        if not hasattr(self, "factorypartner"):
            return 0

        # Only count items that are taking up storage space
        active_statuses = ["AVAILABLE", "PENDING_REVIEW", "RESERVED"]
        return sum(
            waste.quantity
            for waste in self.factorypartner.waste_items.filter(
                status__in=active_statuses
            )
        )

    def get_capacity_percentage(self):
        """Get capacity usage as a percentage"""
        if self.production_capacity:
            return (self.get_current_capacity_usage() / self.production_capacity) * 100
        return 0

    def has_available_capacity(self, additional_quantity=0):
        """Check if factory has available capacity"""
        if not hasattr(self, "factorypartner"):
            return True

        current_usage = self.get_current_capacity_usage()
        return (current_usage + additional_quantity) <= self.production_capacity

    def get_capacity_breakdown(self):
        """Get detailed breakdown of capacity usage by status"""
        if not hasattr(self, "factorypartner"):
            return {}

        breakdown = self.factorypartner.waste_items.values("status").annotate(
            count=Count("id"), total=Sum("quantity")
        )
        return {
            item["status"]: {"count": item["count"], "total": item["total"]}
            for item in breakdown
        }

    def calculate_recommended_capacity(self, time_period_days=30):
        """Calculate recommended capacity based on historical usage patterns"""
        if not hasattr(self, "factory_partner"):
            return None

        from django.db.models import Avg, StdDev
        from django.utils import timezone

        start_date = timezone.now() - timezone.timedelta(days=time_period_days)
        usage_stats = self.factory_partner.waste_items.filter(
            date_added__gte=start_date
        ).aggregate(avg_daily_intake=Avg("quantity"), std_dev=StdDev("quantity"))

        if not usage_stats["avg_daily_intake"]:
            return None

        # Calculate recommended capacity with 2 standard deviations buffer
        daily_intake = usage_stats["avg_daily_intake"]
        buffer = (
            usage_stats["std_dev"] * 2 if usage_stats["std_dev"] else daily_intake * 0.5
        )

        return (daily_intake + buffer) * time_period_days

    class Meta:
        verbose_name_plural = "Factory Details"


class FactoryPartner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    factory_details = models.OneToOneField(FactoryDetails, on_delete=models.CASCADE)
    waste_inventory = models.ManyToManyField("inventory.TextileWaste")

    def upload_waste_details(self, waste):
        # Logic for uploading waste details
        pass

    def view_upload_history(self):
        return self.waste_inventory.all()

    def manage_waste_inventory(self):
        # Logic for managing waste inventory
        pass


class Designer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    portfolio = models.ManyToManyField('designs.Design', related_name='designer_portfolio', blank=True)
    design_stats = models.JSONField(default=dict, blank=True)  # Design statistics
    is_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)

    def approve(self):
        self.is_approved = True
        self.approval_date = timezone.now()
        self.save()

    def view_sales_stats(self):
        return self.design_stats

    def receive_notifications(self, notification):
        # Logic for handling notifications
        pass

    def __str__(self):
        return f"{self.user.username}'s Designer Profile"


class BuyerPreferences(models.Model):
    preferred_materials = models.JSONField(default=list)
    preferred_styles = models.JSONField(default=list)
    size_preferences = models.JSONField(default=dict)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)


class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferences = models.OneToOneField(BuyerPreferences, on_delete=models.CASCADE)
    saved_designs = models.ManyToManyField(
        "designs.Design", related_name="saved_by_buyers"
    )

    def save_design(self, design):
        self.saved_designs.add(design)

    def track_order(self, order_id):
        # Logic for tracking orders
        pass


class AdminLevel(models.TextChoices):
    JUNIOR = "JUNIOR", "Junior"
    SENIOR = "SENIOR", "Senior"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    admin_level = models.CharField(
        max_length=20, choices=AdminLevel.choices, default=AdminLevel.JUNIOR
    )
    permissions = models.JSONField(default=list)  # List of permission strings

    def manage_users(self):
        # User management logic
        pass

    def oversee_transactions(self):
        # Transaction oversight logic
        pass

    def monitor_system_security(self):
        # Security monitoring logic
        pass

    def generate_reports(self):
        # Report generation logic
        pass

    def manage_permissions(self, user_id, permissions):
        # Permission management logic
        pass
