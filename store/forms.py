from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import CartItem, Order, Product, ReturnRequest


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            
            # Use isinstance to safely check widget types without raising AttributeErrors
            if isinstance(field.widget, forms.CheckboxInput):
                base_class = "form-check-input"
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                base_class = "form-select"
            else:
                # TextInputs, NumberInputs, Textareas, FileInputs, etc.
                base_class = "form-control"
                
            field.widget.attrs["class"] = f"{base_class} {existing}".strip()
        # for field in self.fields.values():
        #     existing = field.widget.attrs.get("class", "")
        #     if field.widget.input_type == "checkbox":
        #         base_class = "form-check-input"
        #     elif field.widget.input_type == "select":
        #         base_class = "form-select"
        #     elif field.widget.input_type == "file":
        #         base_class = "form-control"
        #     else:
        #         base_class = "form-control"
        #     field.widget.attrs["class"] = f"{base_class} {existing}".strip()


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "stock_quantity", "category", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}))


class CheckoutForm(BootstrapFormMixin, forms.Form):
    shipping_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]


class OrderStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs["class"] = "form-select"

    class Meta:
        model = Order
        fields = ["status"]


class ReturnRequestForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ["reason", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class InventoryUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stock_quantity"].widget.attrs["class"] = "form-control"
        self.fields["is_active"].widget.attrs["class"] = "form-check-input"

    class Meta:
        model = Product
        fields = ["stock_quantity", "is_active"]

