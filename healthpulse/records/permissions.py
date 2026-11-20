from appointments.models import Appointment
from django.core.exceptions import PermissionDenied

AUTH_STATUSES =[
    Appointment.Status.APPROVED ,
    Appointment.Status.IN_VISIT ,
    Appointment.Status.COMPLETED ,
]

def has_relationship(doctor , patient):
    return Appointment.objects.filter(
    doctor=doctor,
    patient=patient,
    status__in=AUTH_STATUSES
).exists()

def require_relationship(doctor,patient):
    if not has_relationship(doctor,patient):
        raise PermissionDenied(
            "No authorized appointment with this patient."
        )
