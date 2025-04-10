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
            "customizations": forms.Textarea(
                attrs={
                    "class": "json-editor",
                    "rows": 4,
                    "placeholder": '{"color": "red", "size": "M"}',
                }
            )
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an existing design, set max quantity
        if 'initial' in kwargs and 'design' in kwargs['initial']:
            design = kwargs['initial']['design']
            max_qty = design.get_available_quantity()
            self.fields['quantity'].widget.attrs['max'] = max_qty
            if max_qty <= 0:
                self.fields['quantity'].widget.attrs['disabled'] = True
                self.fields['quantity'].help_text = "This design is currently out of stock."
            else:
                self.fields['quantity'].help_text = f"Maximum available: {max_qty}"
    
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "design" in self.fields:
            self.fields["design"].widget.attrs.update({"class": "select2"})

    def clean_customizations(self):
        customizations = self.cleaned_data["customizations"]
        design = self.cleaned_data.get("design")
        if design:
            # Validate customizations against available options
            for option, choice in customizations.items():
                if not design.customization_options.filter(name=option).exists():
                    raise forms.ValidationError(
                        f"Invalid customization option: {option}"
                    )
        return customizations
