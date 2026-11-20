from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from core.models import PatientProfile
from .models import ClinicalEncounter
from .permissions import require_relationship
from django.views.decorators.http import require_POST
from appointments.models import Appointment


@login_required
def patient_medical_chart(request, patient_id):
    patient = get_object_or_404(
        PatientProfile,
        id=patient_id
    )

    doctor = getattr(request.user, "doctorprofile", None)

    if doctor is None:
        raise PermissionDenied

    require_relationship(doctor, patient)

    encounters = ClinicalEncounter.objects.filter(
        doctor=doctor,
        patient=patient
    )

    data = [
        {
            "id": encounter.id,
            "visit_date": encounter.visit_date,
            "chief_complaint": encounter.chief_complaint,
            "diagnosis": encounter.diagnosis,
            "treatment_notes": encounter.treatment_notes,
        }
        for encounter in encounters
    ]

    return JsonResponse({"encounters": data})


@login_required
def encounter_detail(request, encounter_id):
    encounter = get_object_or_404(
        ClinicalEncounter,
        id=encounter_id
    )

    doctor = getattr(request.user, "doctorprofile", None)

    if doctor is None:
        raise PermissionDenied

    require_relationship(doctor, encounter.patient)

    if encounter.doctor != doctor:
        raise PermissionDenied

    return JsonResponse({
        "id": encounter.id,
        "patient_id": encounter.patient.id,
        "visit_date": encounter.visit_date,
        "chief_complaint": encounter.chief_complaint,
        "diagnosis": encounter.diagnosis,
        "treatment_notes": encounter.treatment_notes,
    })


@login_required
@require_POST
def complete_encounter(request, encounter_id):
    # 1. Get the encounter
    encounter = get_object_or_404(
        ClinicalEncounter,
        id=encounter_id
    )

    # 2. Get the logged-in doctor
    doctor = getattr(request.user, "doctorprofile", None)

    if doctor is None:
        raise PermissionDenied

    # 3. Check the doctor's authorization
    require_relationship(doctor, encounter.patient)

    # 4. Make sure this doctor owns the encounter
    if encounter.doctor != doctor:
        raise PermissionDenied

    # 5. Get the appointment linked to this encounter
    appointment = encounter.appointment

    # 6. Check if the appointment is currently in progress
    if appointment.status != Appointment.Status.IN_VISIT:
        return JsonResponse(
            {"error": "Only in-progress appointments can be completed."},
            status=400
        )

    # 7. Change the appointment status
    appointment.status = Appointment.Status.COMPLETED

    # 8. Save the updated status
    appointment.save(update_fields=["status"])

    # 9. Return success response
    return JsonResponse({
        "message": "Encounter completed successfully.",
        "encounter_id": encounter.id,
        "status": appointment.status,
    })
