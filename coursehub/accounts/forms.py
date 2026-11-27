from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User


class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, 'Student'),
            (User.Role.INSTRUCTOR, 'Instructor'),
        ],
        initial=User.Role.STUDENT,
        required=True
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'role',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A user with this email address already exists."
            )

        return email
