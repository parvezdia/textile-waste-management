from django.db import models
from django.utils import timezone


class Dimensions(models.Model):
    length = models.FloatField()
    width = models.FloatField()
    unit = models.CharField(max_length=10)

    def convert_to(self, target_unit):
        # Implementation for unit conversion
        pass

    def __str__(self):
        return f"{self.length}x{self.width} {self.unit}"


class TextileWaste(models.Model):
    WASTE_STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("RESERVED", "Reserved"),
        ("USED", "Used"),
        ("RECYCLED", "Recycled"),
        ("EXPIRED", "Expired"),
        ("PENDING_REVIEW", "Pending Review"),
    ]

    QUALITY_CHOICES = [
        ("EXCELLENT", "Excellent"),
        ("GOOD", "Good"),
        ("FAIR", "Fair"),
        ("POOR", "Poor"),
    ]

    waste_id = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=100)
    material = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, default="kg")
    color = models.CharField(max_length=50)
    dimensions = models.OneToOneField(Dimensions, on_delete=models.CASCADE)
    quality_grade = models.CharField(
        max_length=20, choices=QUALITY_CHOICES, default="GOOD"
    )

    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    expiry_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=WASTE_STATUS_CHOICES, default="PENDING_REVIEW"
    )
    factory = models.ForeignKey(
        "accounts.FactoryPartner", on_delete=models.CASCADE, related_name="waste_items"
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_waste",
    )

    description = models.TextField(blank=True)
    sustainability_score = models.FloatField(default=0)
    storage_location = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)

    def calculate_recycle_potential(self):
        """Calculate recycling potential based on quality, quantity and material type"""
        quality_scores = {"EXCELLENT": 1.0, "GOOD": 0.8, "FAIR": 0.6, "POOR": 0.4}
        base_score = quality_scores.get(self.quality_grade, 0.5)
        quantity_factor = min(1.0, self.quantity / 1000)  # Normalize by 1000 units
        return base_score * quantity_factor * 100  # Returns score from 0-100

    def is_expired(self):
        """Check if the waste item has expired"""
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.status = "EXPIRED"
            self.save()
            return True
        return False

    def update_sustainability_score(self):
        """Update sustainability score based on various factors"""
        recycle_score = self.calculate_recycle_potential()
        time_factor = 1.0
        if self.expiry_date:
            days_until_expiry = (self.expiry_date - timezone.now()).days
            time_factor = min(1.0, max(0.1, days_until_expiry / 365))
        self.sustainability_score = recycle_score * time_factor
        self.save()

    def __str__(self):
        return f"{self.waste_id} - {self.material} ({self.status})"

    class Meta:
        ordering = ["-date_added"]
        permissions = [
            ("can_review_waste", "Can review waste entries"),
            ("can_manage_inventory", "Can manage inventory"),
            ("can_view_analytics", "Can view inventory analytics"),
        ]


class WasteHistory(models.Model):
    waste_item = models.ForeignKey(
        TextileWaste, on_delete=models.CASCADE, related_name="history"
    )
    status = models.CharField(max_length=20, choices=TextileWaste.WASTE_STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Waste histories"
