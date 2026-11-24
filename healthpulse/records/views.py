import os

from django.contrib import messages
from django.utils.dateformat import format as date_format
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from appointments.models import Appointment
from core.decorators import doctor_required, patient_required
from core.models import PatientProfile


from .forms import (
    ClinicalEncounterForm,
    MedicalFileForm,
    MedicalFileFormSet,
    PrescriptionFormSet,
)
from .models import ClinicalEncounter, MedicalFile
from .permissions import has_relationship, require_relationship


def _wants_json(request):
    """API callers (fetch / tests) get JSON; browsers get HTML pages."""
    return (
        request.GET.get("format") == "json"
        or "application/json" in request.META.get("HTTP_ACCEPT", "")
    )


def _wants_html(request):
    return "text/html" in request.META.get("HTTP_ACCEPT", "")


def _encounter_payload(encounter):
    return {
        "id": encounter.id,
        "patient_id": encounter.patient_id,
        "visit_date": encounter.appointment.appointment_date,
        "recorded_on": encounter.visit_date,
        "status": encounter.appointment.status,
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
        "files": [
            {
                "id": medical_file.id,
                "title": medical_file.title,
                "file_type": medical_file.file_type,
            }
            for medical_file in encounter.files.all()
        ],
    }


@login_required
def patient_medical_chart(request, patient_id):
    patient = get_object_or_404(
        PatientProfile.objects.select_related("user"),
        id=patient_id,
    )

    doctor = getattr(request.user, "doctorprofile", None)

    if doctor is None:
        raise PermissionDenied

    require_relationship(doctor, patient)

    encounters = (
        ClinicalEncounter.objects.filter(doctor=doctor, patient=patient)
        .select_related("appointment")
        .prefetch_related("prescriptions", "files")
        .order_by("-appointment__appointment_date", "-id")
    )

    if _wants_json(request):
        return JsonResponse(
            {"encounters": [_encounter_payload(e) for e in encounters]}
        )

    files = patient.files.select_related("encounter").order_by("-uploaded_at")

    return render(
        request,
        "records/patient_chart.html",
        {"patient": patient, "encounters": encounters, "files": files},
    )


@login_required
def encounter_detail(request, encounter_id):
    encounter = get_object_or_404(
        ClinicalEncounter.objects.select_related(
            "appointment", "patient__user", "doctor__user"
        ),
        id=encounter_id,
    )

    doctor = getattr(request.user, "doctorprofile", None)

    if doctor is None:
        raise PermissionDenied

    require_relationship(doctor, encounter.patient)

    if encounter.doctor != doctor:
        raise PermissionDenied

    if _wants_json(request):
        return JsonResponse(_encounter_payload(encounter))

    return render(
        request,
        "records/encounter_detail.html",
        {
            "encounter": encounter,
            "is_in_visit": (
                encounter.appointment.status == Appointment.Status.IN_VISIT
            ),
        },
    )


@login_required
@require_POST
def complete_encounter(request, encounter_id):
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

    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(
            pk=encounter.appointment_id
        )

        if appointment.status != Appointment.Status.IN_VISIT:
            error = "Only in-progress appointments can be completed."
            if _wants_html(request):
                messages.error(request, error)
                return redirect("encounter_detail", encounter_id=encounter.id)
            return JsonResponse({"error": error}, status=400)

        appointment.status = Appointment.Status.COMPLETED
        appointment.save(update_fields=["status"])

    if _wants_html(request):
        messages.success(
            request,
            "Encounter completed. The record is now locked and visible "
            "in the patient's medical history.",
        )
        return redirect("doctor_dashboard")

    return JsonResponse({
        "message": "Encounter completed successfully.",
        "encounter_id": encounter.id,
        "status": appointment.status,
    })


def _render_encounter_form(request, encounter, form, formset, file_formset):
    return render(
        request,
        "records/encounter_form.html",
        {
            "form": form,
            "formset": formset,
            "file_formset": file_formset,
            "encounter": encounter,
        },
    )


@doctor_required
def encounter_create(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related("patient__user"),
        id=appointment_id,
        doctor=request.user.doctorprofile,
    )

    if hasattr(appointment, "encounter"):
        if appointment.status == Appointment.Status.COMPLETED:
            return redirect(
                "encounter_detail", encounter_id=appointment.encounter.id
            )
        return redirect(
            "encounter_edit",
            encounter_id=appointment.encounter.id
        )

    if appointment.status == Appointment.Status.COMPLETED:
        raise PermissionDenied(
            "Cannot create an encounter for a completed appointment."
        )

    # The encounter is recorded during the visit: the doctor must press
    # "Start Visit" (APPROVED -> IN_VISIT) first. Otherwise the encounter
    # could never be completed, because completion requires IN_VISIT.
    if appointment.status != Appointment.Status.IN_VISIT:
        raise PermissionDenied(
            "Start the visit before recording an encounter."
        )

    require_relationship(request.user.doctorprofile, appointment.patient)

    encounter = ClinicalEncounter(
        appointment=appointment,
        patient=appointment.patient,
        doctor=request.user.doctorprofile,
    )

    if request.method == "POST":
        form = ClinicalEncounterForm(request.POST)

        formset = PrescriptionFormSet(
            request.POST,
            instance=encounter
        )

        file_formset = MedicalFileFormSet(
            request.POST,
            request.FILES,
            instance=encounter
        )

        if (
            form.is_valid()
            and formset.is_valid()
            and file_formset.is_valid()
        ):
            with transaction.atomic():
                encounter = form.save(commit=False)
                encounter.appointment = appointment
                encounter.patient = appointment.patient
                encounter.doctor = request.user.doctorprofile
                encounter.save()

                formset.instance = encounter
                file_formset.instance = encounter

                formset.save()
                file_formset.save()

            messages.success(request, "Encounter saved.")
            return redirect(
                "encounter_detail",
                encounter_id=encounter.id
            )

    else:
        form = ClinicalEncounterForm()
        formset = PrescriptionFormSet(instance=encounter)
        file_formset = MedicalFileFormSet(instance=encounter)

    return _render_encounter_form(
        request, encounter, form, formset, file_formset
    )


@doctor_required
def encounter_edit(request, encounter_id):
    encounter = get_object_or_404(
        ClinicalEncounter.objects.select_related(
            "appointment", "patient__user"
        ),
        id=encounter_id,
        doctor=request.user.doctorprofile,
    )

    # Prevent editing completed encounters
    if encounter.appointment.status == Appointment.Status.COMPLETED:
        raise PermissionDenied(
            "Completed encounters cannot be edited."
        )

    if encounter.appointment.status != Appointment.Status.IN_VISIT:
        raise PermissionDenied(
            "Encounters can only be edited while the visit is in progress."
        )

    require_relationship(
        request.user.doctorprofile,
        encounter.patient
    )

    if request.method == "POST":
        form = ClinicalEncounterForm(
            request.POST,
            instance=encounter
        )

        formset = PrescriptionFormSet(
            request.POST,
            instance=encounter
        )

        file_formset = MedicalFileFormSet(
            request.POST,
            request.FILES,
            instance=encounter
        )

        if (
            form.is_valid()
            and formset.is_valid()
            and file_formset.is_valid()
        ):
            with transaction.atomic():
                form.save()
                formset.save()
                file_formset.save()

            messages.success(request, "Encounter updated.")
            return redirect(
                "encounter_detail",
                encounter_id=encounter.id
            )

    else:
        form = ClinicalEncounterForm(instance=encounter)
        formset = PrescriptionFormSet(instance=encounter)
        file_formset = MedicalFileFormSet(instance=encounter)

    return _render_encounter_form(
        request, encounter, form, formset, file_formset
    )


@doctor_required
@require_POST
def start_visit(request, pk):
    appointment = get_object_or_404(
        Appointment,
        pk=pk,
        doctor=request.user.doctorprofile,
    )

    if appointment.status == Appointment.Status.APPROVED and appointment.is_future:
        messages.error(
            request,
            f"This visit is scheduled for {date_format(appointment.appointment_date, 'j M Y')}. "
            "You can start it on that day.",
        )
        return redirect("doctor_dashboard")

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


@login_required
def download_file(request, pk):
    medical_file = get_object_or_404(
        MedicalFile.objects.select_related("patient", "encounter"),
        pk=pk,
    )

    patient = medical_file.patient

    patient_profile = getattr(request.user, "patientprofile", None)
    doctor_profile = getattr(request.user, "doctorprofile", None)

    is_owner = (
        patient_profile is not None
        and patient_profile == patient
    )

    is_authorized_doctor = (
        doctor_profile is not None
        and has_relationship(doctor_profile, patient)
    )

    if not (is_owner or is_authorized_doctor):
        raise PermissionDenied(
            "You do not have permission to access this medical file."
        )

    if not medical_file.file or not os.path.exists(medical_file.file.path):
        raise Http404("Requested file not found.")

    response = FileResponse(
        medical_file.file.open("rb"),
        as_attachment=False,
        filename=os.path.basename(medical_file.file.name),
    )
    # Medical data must never sit in shared/proxy caches.
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@doctor_required
def medical_file_upload(request, patient_id):
    patient = get_object_or_404(
        PatientProfile.objects.select_related("user"),
        id=patient_id,
    )

    require_relationship(request.user.doctorprofile, patient)

    if request.method == "POST":
        form = MedicalFileForm(request.POST, request.FILES)

        if form.is_valid():
            medical_file = form.save(commit=False)
            medical_file.patient = patient
            medical_file.save()

            messages.success(request, "File uploaded.")
            return redirect(
                "patient_medical_chart",
                patient_id=patient.id,
            )

    else:
        form = MedicalFileForm()

    return render(
        request,
        "records/medical_file_upload.html",
        {"form": form, "patient": patient},
    )


@patient_required
def medical_history(request):
    """Patient-facing timeline of their own completed visits."""
    patient = get_object_or_404(PatientProfile, user=request.user)

    encounters = (
        ClinicalEncounter.objects.filter(
            patient=patient,
            appointment__status=Appointment.Status.COMPLETED,
        )
        .select_related("doctor__user", "appointment")
        .prefetch_related(
            "prescriptions",
            Prefetch("files", queryset=MedicalFile.objects.order_by("title")),
        )
        .order_by("-appointment__appointment_date", "-id")
    )

    # Files a doctor uploaded straight to the chart, outside any visit.
    other_files = patient.files.filter(encounter__isnull=True).order_by(
        "-uploaded_at"
    )

    return render(
        request,
        "records/medical_history.html",
        {"encounters": encounters, "other_files": other_files},
    )



@doctor_required
def my_patients(request):
    doc = request.user.doctorprofile
    patients = PatientProfile.objects.filter(
        appointments__doctor=doc,
        appointments__status__in=["APPROVED", "COMPLETED"],
    ).select_related("user").distinct()
    return render(request, "records/my_patients.html", {"patients": patients})