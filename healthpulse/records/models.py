
from django.db import models
from django.core.validators import FileExtensionValidator


class MedicalFile(models.Model):

    class Type(models.TextChoices):
        XRAY = "XRAY", "X-Ray"
        LAB_REPORT = "LAB_REPORT", "Lab Report"
        OTHER = "OTHER", "Other"

    patient = models.ForeignKey(
        "core.PatientProfile",
        on_delete=models.CASCADE,
        related_name="files",
    )

    encounter = models.ForeignKey(
        "appointments.ClinicalEncounter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
    )

    file = models.FileField(
        upload_to="medical/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png"]
            )
        ],
    )

    file_type = models.CharField(
        max_length=12,
        choices=Type.choices,
    )

    title = models.CharField(max_length=150)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
