from django import forms
from django.contrib.auth.models import User
from .models import Customer, Product
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

class CustomerSignupForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password'}),
        min_length=8,
        validators=[
            RegexValidator(
                regex=r'[0-9]',
                message='Password must contain at least one number (0-9).'
            )
        ],
        help_text="Must be at least 8 characters and include a number."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}), 
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone', 'password', 'confirm_password']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        phone = cleaned_data.get("phone")

        if email:
            if User.objects.filter(email=email).exists():
                self.add_error('email', "This email address is already registered.")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        if phone:
            if Customer.objects.filter(phone=phone).exists():
                self.add_error('phone', "This phone number is already registered.")

        return cleaned_data
    
class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100)
    address = forms.CharField()
    apartment = forms.CharField(required=False)
    postcode = forms.CharField(max_length=10)
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)
    save_info = forms.BooleanField(required=False)

    def save_customer_data(self, user):
        user.first_name = self.cleaned_data['full_name']
        user.save()

        if self.cleaned_data['save_info']:
            customer, created = Customer.objects.get_or_create(user=user)
            full_addr = f"{self.cleaned_data['apartment']}, {self.cleaned_data['address']}, {self.cleaned_data['postcode']}, {self.cleaned_data['city']}, {self.cleaned_data['state']}"
            customer.address = full_addr
            customer.phone = self.cleaned_data['phone']
            customer.save()

class ProfileUpdateForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100, label="Full Name")
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = User
        fields = ['full_name', 'email']

    def __init__(self, *args, **kwargs):
        self.customer_instance = kwargs.pop('customer_instance', None)
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        
        # Pre-fill
        if self.instance:
            self.fields['full_name'].initial = self.instance.first_name
        if self.customer_instance:
            self.fields['phone'].initial = self.customer_instance.phone
            self.fields['address'].initial = self.customer_instance.address

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        phone = cleaned_data.get("phone")

        # Check email uniqueness (excluding current user)
        if email:
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                self.add_error('email', "This email address is already registered.")

        # Check phone uniqueness (excluding current customer)
        if phone:
            if Customer.objects.filter(phone=phone).exclude(pk=self.customer_instance.pk).exists():
                self.add_error('phone', "This phone number is already registered.")

        return cleaned_data
    
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'description', 'stock', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control rounded-0'})