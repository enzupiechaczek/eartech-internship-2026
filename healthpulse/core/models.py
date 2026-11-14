
from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patientprofile",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patient: {self.user.username}"


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctorprofile",
    )
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