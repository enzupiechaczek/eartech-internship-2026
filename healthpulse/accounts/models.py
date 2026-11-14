
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "PATIENT", "Patient"
        DOCTOR = "DOCTOR", "Doctor"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def dashboard_url_name(self):
        return {
            self.Role.PATIENT: "patient_dashboard",
            self.Role.DOCTOR: "doctor_dashboard",
        }.get(self.role)



from django.conf import settings
from django.db import models
class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Patient profile: {self.user.username}"
