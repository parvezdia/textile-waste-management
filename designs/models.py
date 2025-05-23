from django.db import models


class Image(models.Model):
    image_id = models.CharField(max_length=100, unique=True)
    filename = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    size = models.IntegerField()
    resolution = models.CharField(max_length=50)
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class Design(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_REVIEW", "Pending Review"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
        ("DELETED", "Deleted"),
    ]

    design_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    designer = models.ForeignKey(
        "accounts.Designer", on_delete=models.CASCADE, related_name="designs"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    required_materials = models.ManyToManyField(
        "inventory.TextileWaste", related_name="designs_requiring"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    date_created = models.DateTimeField(auto_now_add=True)
    # The actual database column is 'last_modified', not 'date_updated'
    last_modified = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to="designs/", null=True, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    estimated_delivery_days = models.IntegerField(default=7)

    @property
    def date_updated(self):
        """Property to maintain compatibility with code that expects date_updated"""
        return self.last_modified

    def calculate_material_cost(self):
        total_cost = 0
        for material in self.required_materials.all():
            # Implement material cost calculation logic
            pass
        return total_cost

    def is_customizable(self):
        return self.customization_options.exists()    
    def get_available_quantity(self):
        """
        Calculate maximum available quantity based on required materials.
        Returns the minimum available quantity across all required materials.
        """
        available_quantities = []
        
        # Consider these statuses as indicating material is available
        available_statuses = ["AVAILABLE", "PENDING_REVIEW", "RESERVED"]
        
        # Include all materials that have any usable status
        for material in self.required_materials.filter(status__in=available_statuses).all():
            # For each material, calculate how many designs can be made
            # based on material quantity available
            if material.quantity > 0:
                available_quantities.append(int(material.quantity))
        
        # If we have no materials or no available quantities, return 12 as default
        # You can adjust this default value as needed for your application
        if not available_quantities:
            return 12
        
        # Return the minimum available quantity (the limiting factor)
        return min(available_quantities)

    def __str__(self):
        return f"{self.name} ({self.design_id})"

    class Meta:
        ordering = ["-date_created"]


class CustomizationOption(models.Model):
    OPTION_TYPES = [
        ("COLOR", "Color"),
        ("SIZE", "Size"),
        ("MATERIAL", "Material"),
        ("STYLE", "Style"),
        ("FEATURE", "Feature"),
    ]

    option_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=OPTION_TYPES)
    available_choices = models.JSONField(help_text="List of available choices")
    price_impact = models.JSONField(help_text="Map of choice to price impact")
    design = models.ForeignKey(
        Design, on_delete=models.CASCADE, related_name="customization_options"
    )

    def __str__(self):
        return f"{self.name} - {self.type}"

    @property
    def choices(self):
        """Return available choices as a list, or default choices based on type if empty"""
        if not self.available_choices or len(self.available_choices) == 0:
            if self.type == "COLOR":
                return ["Red", "Blue", "Green", "Black", "White"]
            elif self.type == "SIZE":
                return ["Small", "Medium", "Large", "X-Large"]
            return []
        return self.available_choices

    @property
    def additional_cost(self):
        """Calculate additional cost based on option type and price impact setting"""
        from decimal import Decimal

        if self.price_impact.get("has_impact", False):
            if self.type == "COLOR":
                # 5% of base price for Color
                return round(self.design.price * Decimal("0.05"), 2)
            elif self.type == "SIZE":
                # 10% of base price for Size
                return round(self.design.price * Decimal("0.10"), 2)
        return Decimal("0.00")
