from django.db import models


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