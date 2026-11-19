from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

from core.models import PatientProfile
from .models import ClinicalEncounter
from .permissions import require_relationship
from appointments.models import Appointment
from .forms import EncounterForm


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
def start_visit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if appt.status == "APPROVED":
        appt.status = "IN_VISIT"
        appt.save()
        return redirect("records:encounter_form", pk=appt.pk)
    return render(request, "visits/visit_detail.html", {"appt": appt})

@login_required
def encounter_form_view(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        form = EncounterForm(request.POST)
        if form.is_valid():
            encounter = form.save(commit=False)
            encounter.appointment = appt
            encounter.patient = appt.patient
            encounter.doctor = getattr(request.user, "doctorprofile", None)
            encounter.save()
            return redirect("records:patient_chart", patient_id=appt.patient.id)
    else:
        form = EncounterForm()
    return render(request, "records/encounter_form.html", {"form": form, "appt": appt})
@login_required
def doctor_dashboard(request):
  doctor = getattr(request.user, "doctorprofile", None)
  if doctor is None:
    raise PermissionDenied

  # جلب المواعيد أو الزيارات الخاصة بهذا الدكتور
  appointments = Appointment.objects.filter(
      doctor=doctor
  )  # أو حسب نموذج المواعيد لديكم

  return render(
      request, "doctor_dashboard.html", {"appointments": appointments}
  )