from django import forms

from .models import DeliveryInfo, Order, PaymentInfo


class PaymentInfoForm(forms.ModelForm):
    class Meta:
        model = PaymentInfo
        fields = ["payment_id", "method", "amount"]
        widgets = {"amount": forms.NumberInput(attrs={"step": "0.01"})}


class DeliveryInfoForm(forms.ModelForm):
    class Meta:
        model = DeliveryInfo
        fields = ["tracking_number", "carrier", "address", "estimated_delivery_date"]
        widgets = {
            "estimated_delivery_date": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["design", "quantity", "customizations"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 1, "class": "form-control", "id": "quantity-input"}),
            "customizations": forms.HiddenInput()  # Changed to hidden input since we'll handle it through session
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing design, set max quantity
        if 'initial' in kwargs and 'design' in kwargs['initial']:
            design_id = kwargs['initial']['design']
            from designs.models import Design
            try:
                # Get the actual Design object if we have an ID
                if isinstance(design_id, int):
                    design = Design.objects.get(id=design_id)
                else:
                    design = design_id
                
                max_qty = design.get_available_quantity()
                self.fields['quantity'].widget.attrs['max'] = max_qty
                if max_qty <= 0:
                    self.fields['quantity'].widget.attrs['disabled'] = True
                    self.fields['quantity'].help_text = "This design is currently out of stock."
                else:
                    self.fields['quantity'].help_text = f"Maximum available: {max_qty}"
            except Exception as e:
                # Fallback to default behavior if we can't get the design
                self.fields['quantity'].widget.attrs['max'] = 10
                self.fields['quantity'].help_text = "Maximum: 10"
                import logging
                logger = logging.getLogger('customization_debug')
                logger.debug(f"Error getting design quantity: {str(e)}")
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        design = self.cleaned_data.get('design')
        
        if design:
            max_available = design.get_available_quantity()
            if quantity > max_available:
                raise forms.ValidationError(
                    f"Sorry, only {max_available} unit(s) of this design are available."
                )
        
        return quantity      
    def clean_customizations(self):
        customizations = self.cleaned_data.get("customizations", {})
        design = self.cleaned_data.get("design")
        
        # If customizations is None or empty string, return empty dict
        if not customizations:
            return {}
            
        # If it's a string (JSON), try to convert to dict
        if isinstance(customizations, str):
            try:
                import json
                customizations = json.loads(customizations)
            except json.JSONDecodeError:
                # If JSON decode fails, log it but don't fail validation
                import logging
                logger = logging.getLogger('customization_debug')
                logger.debug(f"Failed to parse customizations JSON: {customizations}")
                return {}
                
        # Make sure we have a dict
        if not isinstance(customizations, dict):
            return {}
        
        # At this point, customizations should be a valid dict
        return customizations
