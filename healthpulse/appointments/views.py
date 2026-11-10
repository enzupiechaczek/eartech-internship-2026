from django.shortcuts import render

from core.decorators import doctor_required

from .models import Appointment


@doctor_required
def pending_requests(request):
    """Show the logged-in doctor only their own PENDING appointment requests."""
    appts = Appointment.objects.filter(
        doctor=request.user.doctorprofile,
        status=Appointment.Status.PENDING,
    ).select_related('patient__user')
    return render(request, 'appointments/pending.html', {'appts': appts})
