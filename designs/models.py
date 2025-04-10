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
    designer = models.ForeignKey('accounts.Designer', on_delete=models.CASCADE, related_name='designs')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    required_materials = models.ManyToManyField('inventory.TextileWaste', related_name='designs_requiring')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    date_created = models.DateTimeField(auto_now_add=True)
    # The actual database column is 'last_modified', not 'date_updated'
    last_modified = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='designs/', null=True, blank=True)
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
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name='customization_options')

    def __str__(self):
        return f"{self.name} - {self.type}"
