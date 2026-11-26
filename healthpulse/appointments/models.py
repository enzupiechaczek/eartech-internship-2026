from datetime import datetime

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        IN_VISIT = "IN_VISIT", "In visit"
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

    @property
    def starts_at(self):
        return timezone.make_aware(
            datetime.combine(self.appointment_date, self.time_slot)
        )

    @property
    def is_expired(self):
        """A request nobody answered before its start time has passed."""
        return (
            self.status == self.Status.PENDING
            and self.starts_at < timezone.now()
        )

    @staticmethod
    def upcoming_q():
        """Query filter for appointments that have not started yet."""
        now = timezone.localtime()
        return Q(appointment_date__gt=now.date()) | Q(
            appointment_date=now.date(), time_slot__gte=now.time()
        )

    @property
    def is_future(self):
        return self.appointment_date > timezone.localdate()

    @property
    def status_key(self):
        return "EXPIRED" if self.is_expired else self.status

    @property
    def status_label(self):
        return "Expired" if self.is_expired else self.get_status_display()

    