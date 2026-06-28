from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import CustomUser
from .models import Profile, Contact


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password',
    )

    class Meta:
        # Use CustomUser so registration writes directly to the user table.
        model = CustomUser
        fields = ['full_name', 'email', 'password']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            if CustomUser.objects.filter(email__iexact=email).exists():
                raise ValidationError('Email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')

        if password:
            validate_password(password)

        return cleaned_data

    def save(self, commit=True):
        """Create and return a new `CustomUser` with a properly hashed password.

        Ensures a username exists (generated from email) and avoids writing
        plaintext passwords to the database.
        """
        user = super().save(commit=False)
        email = (self.cleaned_data.get('email') or '').strip().lower()
        password = self.cleaned_data.get('password')

        # Ensure a username exists; make it unique using a short uuid suffix.
        if not getattr(user, 'username', None):
            base_username = email.split('@')[0] if email else 'user'
            import uuid as _uuid
            user.username = f"{base_username}_{_uuid.uuid4().hex[:6]}"

        # Normalize and assign email/full name
        user.email = email
        user.full_name = self.cleaned_data.get('full_name', '')

        # Hash password
        if password:
            user.set_password(password)

        # Set sensible defaults for required fields that might not be present
        if not getattr(user, 'mobile_no', None):
            user.mobile_no = ''
        if not getattr(user, 'address', None):
            user.address = ''

        # Mark user inactive until email verification completes
        user.is_active = False
        user.is_email_verified = False

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        }),
        label='Email',
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        }),
        label='Password',
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Remember me',
    )


class OTPVerificationForm(forms.Form):
    email = forms.EmailField(
        required=False,
        widget=forms.HiddenInput(),
    )
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        label='OTP Code',
    )


class TestEmailForm(forms.Form):
    subject = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        initial='Test Email from ShopSphere',
        label='Email Subject',
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        initial='This is a test email sent from Django SMTP configuration. If you receive this, your email setup is working correctly!',
        label='Email Message',
    )
    recipient_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Recipient Email Address',
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'email', 'mobile_no', 'alternate_mobile_no', 'dob', 'address', 'profile_image', 'gender']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'alternate_mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number (optional)'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Your message...'}),
        }

