from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from .models import Admin, AdminLevel, Buyer, ContactInfo, Designer, FactoryDetails, FactoryPartner, User


class UserRegistrationForm(UserCreationForm):
    # Instead of using form.ChoiceField directly, we'll use a model field
    # This ensures the choices are properly handled between display/internal values
    user_type = forms.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "user_type"]

    def clean_user_type(self):
        """Ensure we're using the internal value, not the display value"""
        user_type = self.cleaned_data.get("user_type")
        valid_types = dict(User.USER_TYPE_CHOICES)
        if user_type not in valid_types:
            # If they somehow passed the display value, convert it back
            reverse_types = {v: k for k, v in User.USER_TYPE_CHOICES}
            if user_type in reverse_types:
                return reverse_types[user_type]
            raise forms.ValidationError("Invalid user type selected")
        return user_type


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter your password"}
        )
    )

    def clean(self):
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")

        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password")
            self.user = user
        return self.cleaned_data

    def get_user(self):
        return getattr(self, "user", None)


class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ["address", "phone", "alternate_email"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter phone number"}
            ),
            "alternate_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter alternate email"}
            ),
        }


class FactoryDetailsForm(forms.ModelForm):
    factory_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter factory name"}
        ),
        help_text="Official registered name of your factory",
    )

    location = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Enter complete factory address",
            }
        ),
        help_text="Complete address including city and postal code",
    )

    production_capacity = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter production capacity in kg/month",
            }
        ),
        help_text="Monthly production capacity in kilograms",
    )

    class Meta:
        model = FactoryDetails
        fields = ["factory_name", "location", "production_capacity"]

    def clean_factory_name(self):
        name = self.cleaned_data.get("factory_name")
        if name and len(name.strip()) < 3:
            raise forms.ValidationError(
                "Factory name must be at least 3 characters long"
            )
        return name.strip()

    def clean_production_capacity(self):
        capacity = self.cleaned_data.get("production_capacity")
        if capacity and capacity <= 0:
            raise forms.ValidationError("Production capacity must be greater than 0")
        return capacity


class FactoryPartnerForm(forms.ModelForm):
    class Meta:
        model = FactoryPartner
        fields = []  # No direct fields needed as we'll handle factory_details separately

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "factory_details"):
            self.factory_details = FactoryDetailsForm(
                instance=self.instance.factory_details, prefix="factory_details"
            )
        else:
            self.factory_details = FactoryDetailsForm(prefix="factory_details")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.factory_details.is_valid():
            factory_details = self.factory_details.save()
            instance.factory_details = factory_details
            if commit:
                instance.save()
        return instance


class DesignerForm(forms.ModelForm):
    class Meta:
        model = Designer
        fields = []  # Add any additional designer-specific fields here


class BuyerPreferencesForm(forms.ModelForm):
    class Meta:
        model = Buyer.preferences.field.related_model
        fields = ["preferred_materials", "preferred_styles", "size_preferences", "max_price"]
        widgets = {
            "preferred_materials": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Cotton, Wool"}),
            "preferred_styles": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Casual, Formal"}),
            "size_preferences": forms.Textarea(attrs={"class": "form-control", "placeholder": "e.g. shirt: M, pants: 32"}),
            "max_price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Maximum price"}),
        }

class BuyerForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = []  # Exclude 'preferences' field


class AdminForm(forms.ModelForm):
    admin_level = forms.ChoiceField(
        choices=AdminLevel.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    
    class Meta:
        model = Admin
        fields = ["admin_level"]
