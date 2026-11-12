import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from django.shortcuts import render, get_object_or_404, redirect

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

    form = BookingForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        appt.patient = request.user.patientprofile
        appt.doctor = doctor
        appt.status = Appointment.Status.PENDING
        appt.save()

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

    appointment.status = new_status
    appointment.save(update_fields=['status'])
    return JsonResponse({'id': appointment.pk, 'status': appointment.status})
