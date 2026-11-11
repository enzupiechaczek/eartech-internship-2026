from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR = 'doctor', 'Doctor'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def dashboard_url_name(self):
        """URL name of this user's dashboard, or None if the role has none."""
        return {
            self.Role.PATIENT: 'patient_dashboard',
            self.Role.DOCTOR: 'doctor_dashboard',
        }.get(self.role)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patientprofile')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patient: {self.user.username}"


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctorprofile'
    )

    specialty = models.CharField(max_length=100, blank=True)
    clinic_branch = models.CharField(max_length=150, blank=True)

    profile_picture = models.ImageField(
        upload_to='doctor_profiles/',
        blank=True,
        null=True
    )

    bio = models.TextField(blank=True)
    qualifications = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Doctor: {self.user.username}"