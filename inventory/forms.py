import random

from django import forms
from django.utils import timezone

from .models import Dimensions, TextileWaste, WasteHistory


class DimensionsForm(forms.ModelForm):
    class Meta:
        model = Dimensions
        fields = ["length", "width", "unit"]
        widgets = {
            "length": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "width": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    ("m", "Meters"),
                    ("cm", "Centimeters"),
                    ("inch", "Inches"),
                    ("yard", "Yards"),
                ],
            ),
        }


class TextileWasteForm(forms.ModelForm):
    expiry_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-control",
                "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
            }
        ),
        required=False,
    )

    class Meta:
        model = TextileWaste
        fields = [
            "type",
            "material",
            "quantity",
            "unit",
            "color",
            "quality_grade",
            "description",
            "storage_location",
            "batch_number",
            "expiry_date",
        ]
        widgets = {
            "type": forms.TextInput(attrs={"class": "form-control"}),
            "material": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "unit": forms.Select(
                attrs={"class": "form-control"},
                choices=[
                    ("kg", "Kilograms"),
                    ("g", "Grams"),
                    ("lb", "Pounds"),
                    ("pcs", "Pieces"),
                ],
            ),
            "color": forms.TextInput(attrs={"class": "form-control"}),
            "quality_grade": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "storage_location": forms.TextInput(attrs={"class": "form-control"}),
            "batch_number": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.factory = kwargs.pop("factory", None)
        super().__init__(*args, **kwargs)
        # Update min datetime for expiry_date field to current time
        self.fields["expiry_date"].widget.attrs["min"] = timezone.now().strftime(
            "%Y-%m-%dT%H:%M"
        )

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get("expiry_date")
        if expiry_date and expiry_date < timezone.now():
            raise forms.ValidationError("Expiry date cannot be in the past.")
        return expiry_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.factory:
            instance.factory = self.factory
        if not instance.waste_id:
            # Generate a unique waste ID using timestamp and random string
            timestamp = timezone.now().strftime("%Y%m%d%H%M")
            random_str = "".join(
                random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6)
            )
            instance.waste_id = f"WST-{timestamp}-{random_str}"
        if commit:
            instance.save()
        return instance


class WasteReviewForm(forms.ModelForm):
    class Meta:
        model = TextileWaste
        fields = ["status", "quality_grade", "storage_location", "sustainability_score"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "quality_grade": forms.Select(attrs={"class": "form-control"}),
            "storage_location": forms.TextInput(attrs={"class": "form-control"}),
            "sustainability_score": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.1"}
            ),
        }

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        required=False,
    )

    def save(self, commit=True, reviewer=None):
        instance = super().save(commit=False)
        if reviewer:
            instance.reviewed_by = reviewer
        if commit:
            instance.save()
            # Create history entry
            WasteHistory.objects.create(
                waste_item=instance,
                status=instance.status,
                changed_by=reviewer,
                notes=self.cleaned_data.get("notes", ""),
            )
        return instance
