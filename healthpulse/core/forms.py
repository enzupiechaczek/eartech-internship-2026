from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RoleRegistrationForm(UserCreationForm):
    # Only patients and doctors can self-register; admins are created via createsuperuser.
    ROLE_CHOICES = (
        (User.Role.PATIENT, 'Patient'),
        (User.Role.DOCTOR, 'Doctor'),
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="First Name"
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Last Name"
    )

    email = forms.EmailField(
        required=True,
        label="Email"
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label="Account Type"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name',
            'last_name',
            'email',
            'role',
        )
