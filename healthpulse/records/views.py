from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from core.models import PatientProfile
from .models import ClinicalEncounter
from .permissions import require_relationship


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