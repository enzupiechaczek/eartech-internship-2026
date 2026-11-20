from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from core.decorators import doctor_required
from core.models import PatientProfile
from .models import ClinicalEncounter
from .permissions import AUTH_STATUSES, require_relationship
from .forms import ClinicalEncounterForm, PrescriptionFormSet
from .forms import ClinicalEncounterForm, PrescriptionFormSet, MedicalFileForm

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

    if (
        request.GET.get("format") == "json"
        or "application/json" in request.META.get("HTTP_ACCEPT", "")
    ):
        return JsonResponse({
            "id": encounter.id,
            "patient_id": encounter.patient.id,
            "visit_date": encounter.visit_date,
            "chief_complaint": encounter.chief_complaint,
            "diagnosis": encounter.diagnosis,
            "treatment_notes": encounter.treatment_notes,
            "prescriptions": [
                {
                    "id": prescription.id,
                    "medication_name": prescription.medication_name,
                    "dosage": prescription.dosage,
                    "frequency": prescription.frequency,
                    "duration": prescription.duration,
                    "instructions": prescription.instructions,
                }
                for prescription in encounter.prescriptions.all()
            ],
        })

    return render(
        request,
        "records/encounter_detail.html",
        {"encounter": encounter},
    )


@doctor_required
def encounter_create(request, appointment_id):
    from appointments.models import Appointment

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=request.user.doctorprofile,
    )

    if appointment.status not in AUTH_STATUSES:
        raise PermissionDenied("Encounter creation requires an approved or active appointment.")

    require_relationship(request.user.doctorprofile, appointment.patient)

    if hasattr(appointment, "encounter"):
        return redirect("encounter_edit", encounter_id=appointment.encounter.id)

    encounter = ClinicalEncounter(
        appointment=appointment,
        patient=appointment.patient,
        doctor=request.user.doctorprofile,
    )
    if request.method == "POST":
        form = ClinicalEncounterForm(request.POST)
        formset = PrescriptionFormSet(request.POST, instance=encounter)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                encounter = form.save(commit=False)
                encounter.appointment = appointment
                encounter.patient = appointment.patient
                encounter.doctor = request.user.doctorprofile
                encounter.save()
                formset.instance = encounter
                formset.save()
            return redirect("encounter_detail", encounter_id=encounter.id)
    else:
        form = ClinicalEncounterForm()
        formset = PrescriptionFormSet(instance=encounter)

    return render(
        request,
        "records/encounter_form.html",
        {"form": form, "formset": formset, "encounter": encounter},
    )


@doctor_required
def encounter_edit(request, encounter_id):
    encounter = get_object_or_404(
        ClinicalEncounter,
        id=encounter_id,
        doctor=request.user.doctorprofile,
    )

    if encounter.appointment.status not in AUTH_STATUSES:
        raise PermissionDenied("Encounter editing requires an approved or active appointment.")

    require_relationship(request.user.doctorprofile, encounter.patient)
    if request.method == "POST":
        form = ClinicalEncounterForm(request.POST, instance=encounter)
        formset = PrescriptionFormSet(request.POST, instance=encounter)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            return redirect("encounter_detail", encounter_id=encounter.id)
    else:
        form = ClinicalEncounterForm(instance=encounter)
        formset = PrescriptionFormSet(instance=encounter)

    return render(
        request,
        "records/encounter_form.html",
        {"form": form, "formset": formset, "encounter": encounter},
    )

@doctor_required
def start_visit(request, pk):
    from appointments.models import Appointment

    if request.method != "POST":
        raise PermissionDenied("Starting a visit requires POST.")

    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        doctor=request.user.doctorprofile,
    )

    if appointment.status == Appointment.Status.APPROVED:
        require_relationship(
            request.user.doctorprofile,
            appointment.patient,
        )
        appointment.status = Appointment.Status.IN_VISIT
        appointment.save(update_fields=["status"])

    elif appointment.status != Appointment.Status.IN_VISIT:
        raise PermissionDenied(
            "Only approved appointments can be started."
        )

    return redirect(
        "encounter_create",
        appointment_id=appointment.pk,
    )
@doctor_required
def medical_file_upload(request, patient_id):
    patient = get_object_or_404(PatientProfile, id=patient_id)

    require_relationship(request.user.doctorprofile, patient)

    if request.method == "POST":
        form = MedicalFileForm(request.POST, request.FILES)
        if form.is_valid():
            medical_file = form.save(commit=False)
            medical_file.patient = patient
            medical_file.save()
            return redirect("patient_medical_chart", patient_id=patient.id)
    else:
        form = MedicalFileForm()

    return render(
        request,
        "records/medical_file_upload.html",
        {"form": form, "patient": patient},
    )