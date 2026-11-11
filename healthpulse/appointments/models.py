
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        IN_VISIT = "IN_VISIT", "In Visit"
        COMPLETED = "COMPLETED", "Completed"

    patient = models.ForeignKey(
        "core.PatientProfile",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    doctor = models.ForeignKey(
        "core.DoctorProfile",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    appointment_date = models.DateField()
    time_slot = models.TimeField()
    reason_for_visit = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["appointment_date", "time_slot"]

    def __str__(self):
        return f"{self.patient} - {self.doctor} - {self.appointment_date}"
