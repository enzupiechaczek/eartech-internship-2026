import json

from django.contrib import messages
from django.utils.dateformat import format as date_format
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import doctor_required, patient_required
from core.models import DoctorProfile

from .models import Appointment
from .forms import BookingForm


@doctor_required
def pending_requests(request):
    """Show the logged-in doctor only their own PENDING appointment requests."""
    appts = Appointment.objects.filter(
        doctor=request.user.doctorprofile,
        status=Appointment.Status.PENDING,
    ).select_related('patient__user')

    return render(request, 'appointments/pending.html', {'appts': appts})


@patient_required
def book(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
    patient_profile = getattr(request.user, "patientprofile", None)

    if patient_profile is None:
        messages.error(
            request,
            "Your patient profile is missing. Please contact support.",
        )
        return redirect("patient_dashboard")

    form = BookingForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        appt.patient = patient_profile
        appt.doctor = doctor
        appt.status = Appointment.Status.PENDING
        appt.save()

        messages.success(
            request,
            f"Appointment requested for {date_format(appt.appointment_date, 'j M Y')} "
            f"at {appt.time_slot:%H:%M}. "
            "You'll see it here once the doctor responds.",
        )
        return redirect("patient_dashboard")

    return render(
        request,
        "appointments/book.html",
        {"form": form, "doctor": doctor},
    )
@doctor_required
@require_POST
def update_status(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        doctor=request.user.doctorprofile,
    )

    try:
        payload = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid transition'}, status=400)

    new_status = payload.get('status') if isinstance(payload, dict) else None
    valid_statuses = (
        Appointment.Status.APPROVED,
        Appointment.Status.REJECTED,
    )
    if (
        appointment.status != Appointment.Status.PENDING
        or new_status not in valid_statuses
    ):
        return JsonResponse({'error': 'invalid transition'}, status=400)

    if new_status == Appointment.Status.APPROVED and appointment.is_expired:
        return JsonResponse({'error': 'This request has expired.'}, status=400)

    appointment.status = new_status
    appointment.save(update_fields=['status'])
    return JsonResponse({'id': appointment.pk, 'status': appointment.status})
