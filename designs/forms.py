from django import forms
from django.core.files.images import get_image_dimensions
import uuid

from inventory.models import TextileWaste, Dimensions
from .models import CustomizationOption, Design, Image


class DesignForm(forms.ModelForm):
    is_customizable = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Enable customization options for this design"
    )

    class Meta:
        model = Design
        fields = [
            "name",
            "description",
            "price",
            "status",
            "image",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['is_customizable'].initial = self.instance.is_customizable()

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            w, h = get_image_dimensions(image)
            if w > 4096 or h > 4096:
                raise forms.ValidationError("Image is too large. Maximum dimensions are 4096x4096px.")
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file is too large. Maximum size is 5MB.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        # Additional validation if needed
        return cleaned_data

    def save(self, commit=True):
        design = super().save(commit=False)
        if commit:
            if not design.design_id:
                design.design_id = f"DES_{uuid.uuid4().hex[:8]}"
            design.save()
        return design


class CustomizationOptionForm(forms.ModelForm):
    # Replace complex price_impact field with simple Yes/No choice
    price_impact = forms.ChoiceField(
        choices=[('Yes', 'Yes'), ('No', 'No')],
        initial='No',
        help_text="Will this customization option affect the price?"
    )
    
    class Meta:
        model = CustomizationOption
        fields = ["name", "type", "price_impact"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:  # If this is a new instance
            self.instance.option_id = f"OPT_{uuid.uuid4().hex[:8]}"
        
        # Restrict option types to only Color and Size
        self.fields['type'].choices = [
            ("COLOR", "Color"),
            ("SIZE", "Size"),
        ]
        
        # If we have an existing instance with price_impact data, set the form field accordingly
        if self.instance.pk and isinstance(self.instance.price_impact, dict):
            self.initial['price_impact'] = 'Yes' if self.instance.price_impact.get('has_impact') else 'No'
        
    def clean_price_impact(self):
        impact_choice = self.cleaned_data["price_impact"]
        # Convert Yes/No to a simple dictionary format expected by the model
        if impact_choice == 'Yes':
            return {"has_impact": True}
        else:
            return {"has_impact": False}
            
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set default available_choices based on option type
        if not instance.available_choices or len(instance.available_choices) == 0:
            if instance.type == "COLOR":
                instance.available_choices = ["Red", "Blue", "Green", "Black", "White"]
            elif instance.type == "SIZE":
                instance.available_choices = ["Small", "Medium", "Large", "X-Large"]
            else:
                instance.available_choices = []
        
        if commit:
            instance.save()
        return instance


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ["image_id", "filename", "path", "size", "resolution"]


class MaterialRequirementForm(forms.ModelForm):
    quantity_required = forms.DecimalField(min_value=0.01, required=True)
    length = forms.DecimalField(min_value=0.01, required=True)
    width = forms.DecimalField(min_value=0.01, required=True)
    unit = forms.ChoiceField(choices=[('m', 'Meters'), ('cm', 'Centimeters'), ('in', 'Inches')], required=True)

    class Meta:
        model = TextileWaste
        fields = ['material', 'type', 'color', 'quality_grade']
        labels = {
            'material': 'Material Type',
            'type': 'Material Category',
            'color': 'Color',
            'quality_grade': 'Minimum Quality Required'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].required = True
        self.fields['type'].required = True
        self.fields['quality_grade'].required = True
        self.fields['material'].widget.attrs.update({'class': 'select2'})
        self.fields['type'].widget.attrs.update({'class': 'select2'})

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('material'):
            self.add_error('material', 'Material type is required')
        if not cleaned_data.get('type'):
            self.add_error('type', 'Material category is required')
        if not cleaned_data.get('quality_grade'):
            self.add_error('quality_grade', 'Quality grade is required')
        if not cleaned_data.get('quantity_required'):
            self.add_error('quantity_required', 'Quantity is required')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Generate a unique waste_id
        instance.waste_id = f"DESIGN_REQ_{uuid.uuid4().hex[:8]}"
        
        # Create and associate dimensions
        dimensions = Dimensions.objects.create(
            length=self.cleaned_data['length'],
            width=self.cleaned_data['width'],
            unit=self.cleaned_data['unit']
        )
        instance.dimensions = dimensions
        
        # Set the actual quantity from quantity_required
        instance.quantity = self.cleaned_data['quantity_required']
        
        # Set default status for design requirements
        instance.status = "PENDING_REVIEW"
        
        if commit:
            instance.save()
        return instance
