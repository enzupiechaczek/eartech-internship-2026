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