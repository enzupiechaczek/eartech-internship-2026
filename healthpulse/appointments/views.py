
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
