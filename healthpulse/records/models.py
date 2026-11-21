from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
def validate_file_size(file):
    if file.size > 10 * 1024 * 1024:
        raise ValidationError("Maximum file size is 10 MB.")

class ClinicalEncounter(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="encounter",
    )
    patient = models.ForeignKey(
        "core.PatientProfile",
        on_delete=models.PROTECT,
        related_name="encounters",
    )
    doctor = models.ForeignKey(
        "core.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="encounters",
    )
    visit_date = models.DateField(auto_now_add=True)
    chief_complaint = models.TextField()
    diagnosis = models.CharField(max_length=255)
    treatment_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self):
        return f"Encounter #{self.pk} - {self.patient} ({self.visit_date})"


class Prescription(models.Model):
    encounter = models.ForeignKey(
        ClinicalEncounter,
        on_delete=models.CASCADE,
        related_name="prescriptions",
    )
    medication_name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)
    duration = models.CharField(max_length=50)
    instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.medication_name} - {self.encounter}"



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
        "records.ClinicalEncounter",
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
            ),
            validate_file_size,
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
