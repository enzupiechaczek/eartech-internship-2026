import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

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
