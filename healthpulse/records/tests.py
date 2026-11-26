from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from unittest.mock import patch
from core.models import DoctorProfile, PatientProfile
from appointments.models import Appointment
from .forms import ClinicalEncounterForm, PrescriptionFormSet
from .models import ClinicalEncounter, Prescription, MedicalFile
from .permissions import has_relationship, require_relationship
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class DoctorPatientRelationshipTests(TestCase):

    def setUp(self):
        # Create doctor user
        self.doctor_user = User.objects.create_user(
            username="doctor1", password="test123"
        )
        self.doctor_user.role = User.Role.DOCTOR
        self.doctor_user.save()

        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)

        # Create patient user
        self.patient_user = User.objects.create_user(
            username="patient1", password="test123"
        )

        self.patient = PatientProfile.objects.create(user=self.patient_user)

    def create_appointment(self, status):
        return Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-20",
            time_slot="10:00",
            reason_for_visit="General checkup",
            status=status,
        )

    # Allowed statuses

    def test_approved_authorizes(self):
        self.create_appointment(Appointment.Status.APPROVED)

        self.assertTrue(has_relationship(self.doctor, self.patient))

    def test_in_visit_appointment_allows_relationship(self):
        self.create_appointment(Appointment.Status.IN_VISIT)

        self.assertTrue(has_relationship(self.doctor, self.patient))

    def test_completed_appointment_allows_relationship(self):
        self.create_appointment(Appointment.Status.COMPLETED)

        self.assertTrue(has_relationship(self.doctor, self.patient))

    # Rejected statuses

    def test_pending_does_not_authorize(self):
        self.create_appointment(Appointment.Status.PENDING)

        self.assertFalse(has_relationship(self.doctor, self.patient))

    def test_rejected_appointment_denies_relationship(self):
        self.create_appointment(Appointment.Status.REJECTED)

        self.assertFalse(has_relationship(self.doctor, self.patient))

    def test_no_appointment_denies_relationship(self):
        self.assertFalse(has_relationship(self.doctor, self.patient))

    def test_appointment_for_different_doctor_patient_pair_denies_relationship(self):
        other_doctor_user = User.objects.create_user(
            username="doctor2",
            password="test123",
        )
        other_doctor = DoctorProfile.objects.create(user=other_doctor_user)
        self.create_appointment(Appointment.Status.APPROVED)

        self.assertFalse(has_relationship(other_doctor, self.patient))

    def test_any_approved_appointment_authorizes_among_multiple_appointments(self):
        self.create_appointment(Appointment.Status.PENDING)
        self.create_appointment(Appointment.Status.APPROVED)

        self.assertTrue(has_relationship(self.doctor, self.patient))

    # require_relationship tests

    def test_require_relationship_allows_authorized_doctor(self):
        self.create_appointment(Appointment.Status.APPROVED)

        try:
            require_relationship(self.doctor, self.patient)
        except PermissionDenied:
            self.fail("Authorized doctor was denied access.")

    def test_require_relationship_denies_unauthorized_doctor(self):
        with self.assertRaises(PermissionDenied):
            require_relationship(self.doctor, self.patient)

    # Patient chart view tests

    def test_authorized_doctor_can_access_patient_chart(self):
        self.create_appointment(Appointment.Status.APPROVED)
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("patient_medical_chart", kwargs={"patient_id": self.patient.id})
        )

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_doctor_gets_403_for_patient_chart(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("patient_medical_chart", kwargs={"patient_id": self.patient.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_non_doctor_gets_403_for_patient_chart(self):
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse("patient_medical_chart", kwargs={"patient_id": self.patient.id})
        )
        self.assertEqual(response.status_code, 403)

    # Encounter detail view tests

    def test_authorized_doctor_can_access_encounter_detail(self):
        appointment = self.create_appointment(Appointment.Status.APPROVED)

        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_detail", kwargs={"encounter_id": encounter.id})
        )

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_doctor_gets_403_for_encounter_detail(self):
        appointment = self.create_appointment(Appointment.Status.PENDING)

        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_detail", kwargs={"encounter_id": encounter.id})
        )

        self.assertEqual(response.status_code, 403)

    # Doctor ownership test

    def test_doctor_cannot_access_another_doctors_encounter(self):
        appointment = self.create_appointment(Appointment.Status.APPROVED)

        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        other_user = User.objects.create_user(username="doctor2", password="test123")
        other_user.role = User.Role.DOCTOR
        other_user.save()

        other_doctor = DoctorProfile.objects.create(user=other_user)
        Appointment.objects.create(
            doctor=other_doctor,
            patient=self.patient,
            appointment_date="2026-11-20",
            time_slot="11:00",
            reason_for_visit="Checkup",
            status=Appointment.Status.APPROVED,
        )

        self.client.force_login(other_user)

        response = self.client.get(
            reverse("encounter_detail", kwargs={"encounter_id": encounter.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_can_complete_in_visit_encounter(self):
        # 1. Create an appointment with IN_VISIT status
        appointment = self.create_appointment(Appointment.Status.IN_VISIT)

        # 2. Create a medical encounter linked to the appointment
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Send a POST request to complete the encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # 5. Refresh appointment data from the database
        appointment.refresh_from_db()

        # 6. Check the result
        self.assertEqual(response.status_code, 200)
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_another_doctor_cannot_complete_encounter(self):
        # Create an appointment for the original doctor
        appointment = self.create_appointment(Appointment.Status.IN_VISIT)

        # Create an encounter for that appointment
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # Create another doctor
        other_user = User.objects.create_user(username="doctor2", password="test123")
        other_user.role = User.Role.DOCTOR
        other_user.save()

        other_doctor = DoctorProfile.objects.create(user=other_user)

        # Give the other doctor an authorized appointment
        Appointment.objects.create(
            doctor=other_doctor,
            patient=self.patient,
            appointment_date="2026-11-20",
            time_slot="11:00",
            reason_for_visit="Checkup",
            status=Appointment.Status.APPROVED,
        )

        # Log in as the other doctor
        self.client.force_login(other_user)

        # Try to complete the original doctor's encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # Check that access is denied
        self.assertEqual(response.status_code, 403)

        # Check that the appointment is still in progress
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_VISIT)

    def test_patient_cannot_complete_encounter(self):
        # Create an appointment with IN_VISIT status
        appointment = self.create_appointment(Appointment.Status.IN_VISIT)

        # Create a clinical encounter
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # Log in as the patient
        self.client.force_login(self.patient_user)

        # Try to complete the encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # Check that access is denied
        self.assertEqual(response.status_code, 403)

        # Check that the appointment status did not change
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_VISIT)

    def test_unauthenticated_user_cannot_complete_encounter(self):
        # Create an appointment with IN_VISIT status
        appointment = self.create_appointment(Appointment.Status.IN_VISIT)

        # Create a clinical encounter
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # Do not log in any user

        # Try to complete the encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # Check that the user is redirected to login
        self.assertEqual(response.status_code, 302)

        # Check that the appointment status did not change
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_VISIT)

    def test_pending_appointment_cannot_be_completed(self):
        # 1. Create a pending appointment
        appointment = self.create_appointment(Appointment.Status.PENDING)

        # 2. Create a clinical encounter
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to complete the encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # 5. Check that access is denied
        self.assertEqual(response.status_code, 403)

        # 6. Check that the status did not change
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)

    def test_completed_appointment_cannot_be_completed_again(self):
        # 1. Create an already completed appointment
        appointment = self.create_appointment(Appointment.Status.COMPLETED)

        # 2. Create a clinical encounter
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to complete the encounter again
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # 5. Check that the request is rejected
        self.assertEqual(response.status_code, 400)

        # 6. Check that the appointment remains completed
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)

    def test_nonexistent_encounter_returns_404(self):
        # 1. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 2. Try to complete a nonexistent encounter
        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": 99999})
        )

        # 3. Check that the encounter was not found
        self.assertEqual(response.status_code, 404)

    def test_get_request_cannot_complete_encounter(self):
        # 1. Create an appointment in progress
        appointment = self.create_appointment(Appointment.Status.IN_VISIT)

        # 2. Create a clinical encounter
        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to complete using GET
        response = self.client.get(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id})
        )

        # 5. Check that GET is not allowed
        self.assertEqual(response.status_code, 405)

        # 6. Check that the appointment is unchanged
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_VISIT)


class PrescriptionTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            username="prescription-doctor",
            password="test123",
            role=User.Role.DOCTOR,
        )
        self.patient_user = User.objects.create_user(
            username="prescription-patient",
            password="test123",
            role=User.Role.PATIENT,
        )
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-20",
            time_slot="10:00",
            reason_for_visit="General checkup",
            status=Appointment.Status.IN_VISIT,
        )
        self.encounter = ClinicalEncounter.objects.create(
            appointment=self.appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest",
        )

    def test_multiple_prescriptions_can_be_associated_with_encounter(self):
        Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )
        Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Atorvastatin",
            dosage="20mg",
            frequency="Nightly",
            duration="90 days",
        )

        self.assertEqual(self.encounter.prescriptions.count(), 2)

    def test_prescription_formset_displays_existing_prescriptions(self):
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )
        formset = PrescriptionFormSet(instance=self.encounter)
        self.assertEqual(formset.initial_form_count(), 1)
        self.assertEqual(
            formset.forms[0].instance.pk,
            prescription.pk,
        )

        self.client.force_login(self.doctor_user)
        response = self.client.get(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aspirin")

    def test_invalid_formset_prevents_encounter_save(self):
        form = ClinicalEncounterForm(
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "",
            },
            instance=self.encounter,
        )
        formset = PrescriptionFormSet(
            {
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
            },
            instance=self.encounter,
        )

        self.assertTrue(form.is_valid())
        self.assertFalse(formset.is_valid())

    def test_formset_can_delete_existing_prescription(self):
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )
        formset = PrescriptionFormSet(
            {
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "1",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-id": str(prescription.id),
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "prescriptions-0-DELETE": "on",
            },
            instance=self.encounter,
        )

        self.assertTrue(formset.is_valid())
        formset.save()
        self.assertFalse(Prescription.objects.filter(pk=prescription.pk).exists())

    def test_create_view_saves_multiple_prescriptions_after_encounter(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-21",
            time_slot="11:00",
            reason_for_visit="Follow-up",
            status=Appointment.Status.IN_VISIT,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": appointment.id},
            ),
            {
                "chief_complaint": "High cholesterol",
                "diagnosis": "Hyperlipidemia",
                "treatment_notes": "Diet and exercise",
                "prescriptions-TOTAL_FORMS": "2",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "prescriptions-1-medication_name": "Atorvastatin",
                "prescriptions-1-dosage": "20mg",
                "prescriptions-1-frequency": "Nightly",
                "prescriptions-1-duration": "90 days",
                "prescriptions-1-instructions": "Take after dinner",
                "files-TOTAL_FORMS": "1",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        encounter = ClinicalEncounter.objects.get(appointment=appointment)
        self.assertRedirects(
            response,
            reverse(
                "encounter_detail",
                kwargs={"encounter_id": encounter.id},
            ),
        )
        self.assertEqual(encounter.prescriptions.count(), 2)

    def test_create_view_does_not_save_invalid_formset(self):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-22",
            time_slot="12:00",
            reason_for_visit="Checkup",
            status=Appointment.Status.IN_VISIT,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": appointment.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "",
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ClinicalEncounter.objects.filter(appointment=appointment).exists()
        )

    def test_edit_view_updates_encounter_and_adds_prescription(self):
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": "Updated complaint",
                "diagnosis": "Updated diagnosis",
                "treatment_notes": "Updated notes",
                "prescriptions-TOTAL_FORMS": "2",
                "prescriptions-INITIAL_FORMS": "1",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-id": str(prescription.id),
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Twice daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "After meals",
                "prescriptions-1-medication_name": "Atorvastatin",
                "prescriptions-1-dosage": "20mg",
                "prescriptions-1-frequency": "Nightly",
                "prescriptions-1-duration": "90 days",
                "prescriptions-1-instructions": "Take after dinner",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "encounter_detail",
                kwargs={"encounter_id": self.encounter.id},
            ),
        )
        self.encounter.refresh_from_db()
        prescription.refresh_from_db()
        self.assertEqual(self.encounter.diagnosis, "Updated diagnosis")
        self.assertEqual(prescription.frequency, "Twice daily")
        self.assertEqual(self.encounter.prescriptions.count(), 2)

    def test_edit_view_deletes_existing_prescription(self):
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "Rest",
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "1",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-id": str(prescription.id),
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "prescriptions-0-DELETE": "on",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Prescription.objects.filter(pk=prescription.pk).exists())

    def test_empty_optional_prescription_row_is_accepted(self):
        formset = PrescriptionFormSet(
            {
                "prescriptions-TOTAL_FORMS": "2",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "",
                "prescriptions-0-dosage": "",
                "prescriptions-0-frequency": "",
                "prescriptions-0-duration": "",
                "prescriptions-0-instructions": "",
                "prescriptions-1-medication_name": "",
                "prescriptions-1-dosage": "",
                "prescriptions-1-frequency": "",
                "prescriptions-1-duration": "",
                "prescriptions-1-instructions": "",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
            instance=self.encounter,
        )

        self.assertTrue(formset.is_valid())
        formset.save()
        self.assertEqual(self.encounter.prescriptions.count(), 0)

    def test_patient_cannot_create_or_edit_encounter(self):
        self.client.force_login(self.patient_user)

        create_response = self.client.get(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": self.appointment.id},
            )
        )
        edit_response = self.client.get(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            )
        )

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(edit_response.status_code, 302)

    def test_unrelated_doctor_cannot_create_or_edit_encounter(self):
        other_user = User.objects.create_user(
            username="other-doctor",
            password="test123",
            role=User.Role.DOCTOR,
        )
        other_doctor = DoctorProfile.objects.create(user=other_user)
        self.client.force_login(other_user)

        create_response = self.client.get(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": self.appointment.id},
            )
        )
        edit_response = self.client.get(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            )
        )

        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(edit_response.status_code, 404)
        self.assertIsNotNone(other_doctor)

    def test_pending_appointment_cannot_be_used_to_create_encounter(self):
        pending = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-23",
            time_slot="13:00",
            reason_for_visit="Pending checkup",
            status=Appointment.Status.PENDING,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": pending.id},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_encounter_detail_url_is_under_records_prefix(self):
        url = reverse(
            "encounter_detail",
            kwargs={"encounter_id": self.encounter.id},
        )

        self.assertEqual(
            url,
            f"/records/encounters/{self.encounter.id}/",
        )

    def test_completed_encounter_cannot_be_edited(self):
        # 1. Mark the appointment as completed
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save(update_fields=["status"])

        # 2. Create an existing prescription
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )

        # 3. Save the original diagnosis
        original_diagnosis = self.encounter.diagnosis

        # 4. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 5. Try to edit the completed encounter
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {"diagnosis": "Updated diagnosis"},
        )

        # 6. Check that access is denied
        self.assertEqual(response.status_code, 403)

        # 7. Refresh the data from the database
        self.encounter.refresh_from_db()
        prescription.refresh_from_db()

        # 8. Make sure nothing was changed
        self.assertEqual(
            self.encounter.diagnosis,
            original_diagnosis,
        )
        self.assertEqual(
            prescription.medication_name,
            "Aspirin",
        )

    def test_completed_encounter_cannot_add_prescription(self):
        # 1. Mark the appointment as completed
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save(update_fields=["status"])

        # 2. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 3. Try to add a new prescription
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "Rest",
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "New Medicine",
                "prescriptions-0-dosage": "10mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "5 days",
                "prescriptions-0-instructions": "",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        # 4. Check that the request is rejected
        self.assertEqual(response.status_code, 403)

        # 5. Make sure no prescription was created
        self.assertEqual(
            self.encounter.prescriptions.count(),
            0,
        )

    def test_completed_encounter_cannot_delete_prescription(self):
        # 1. Complete the appointment
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save(update_fields=["status"])

        # 2. Create an existing prescription
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to delete the prescription
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": self.encounter.chief_complaint,
                "diagnosis": self.encounter.diagnosis,
                "treatment_notes": self.encounter.treatment_notes,
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "1",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-id": str(prescription.id),
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "prescriptions-0-DELETE": "on",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        # 5. Check that the request is rejected
        self.assertEqual(response.status_code, 403)

        # 6. Make sure the prescription still exists
        self.assertTrue(Prescription.objects.filter(pk=prescription.pk).exists())

    @patch(
        "records.views.PrescriptionFormSet.save",
        side_effect=RuntimeError("Simulated prescription save failure"),
    )
    def test_create_view_rolls_back_encounter_when_prescription_save_fails(
        self, mock_save
    ):
        # 1. Create an approved appointment
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-23",
            time_slot="11:00",
            reason_for_visit="General checkup",
            status=Appointment.Status.IN_VISIT,
        )

        # 2. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 3. Capture the server error as a response
        self.client.raise_request_exception = False

        # 4. Submit valid encounter and prescription data
        response = self.client.post(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": appointment.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "Rest",
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        # 5. Check that the save operation failed
        self.assertEqual(response.status_code, 500)
        mock_save.assert_called_once()

        # 6. Make sure the encounter was rolled back
        self.assertFalse(
            ClinicalEncounter.objects.filter(appointment=appointment).exists()
        )

    def test_edit_view_rolls_back_changes_when_prescription_save_fails(self):
        # Create an existing prescription
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )

        original_diagnosis = self.encounter.diagnosis
        original_frequency = prescription.frequency

        self.client.force_login(self.doctor_user)
        self.client.raise_request_exception = False

        original_save = PrescriptionFormSet.save

        def save_then_fail(formset, *args, **kwargs):
            original_save(formset, *args, **kwargs)
            raise RuntimeError("Simulated save failure")

        with patch(
            "records.views.PrescriptionFormSet.save",
            autospec=True,
            side_effect=save_then_fail,
        ) as mock_save:

            response = self.client.post(
                reverse(
                    "encounter_edit",
                    kwargs={"encounter_id": self.encounter.id},
                ),
                {
                    "chief_complaint": self.encounter.chief_complaint,
                    "diagnosis": "Updated diagnosis",
                    "treatment_notes": self.encounter.treatment_notes,
                    "prescriptions-TOTAL_FORMS": "1",
                    "prescriptions-INITIAL_FORMS": "1",
                    "prescriptions-MIN_NUM_FORMS": "0",
                    "prescriptions-MAX_NUM_FORMS": "1000",
                    "prescriptions-0-id": str(prescription.id),
                    "prescriptions-0-medication_name": "Aspirin",
                    "prescriptions-0-dosage": "81mg",
                    "prescriptions-0-frequency": "Twice daily",
                    "prescriptions-0-duration": "30 days",
                    "prescriptions-0-instructions": "",
                    "files-TOTAL_FORMS": "1",
                    "files-INITIAL_FORMS": "0",
                    "files-MIN_NUM_FORMS": "0",
                    "files-MAX_NUM_FORMS": "1000",
                },
            )

        self.assertEqual(response.status_code, 500)
        mock_save.assert_called_once()

        self.encounter.refresh_from_db()
        prescription.refresh_from_db()

        self.assertEqual(
            self.encounter.diagnosis,
            original_diagnosis,
        )
        self.assertEqual(
            prescription.frequency,
            original_frequency,
        )

    def test_create_view_saves_medical_file_with_encounter_and_patient(self):
        # 1. Create an in-visit appointment (visit already started)
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-24",
            time_slot="11:00",
            reason_for_visit="Diagnostic examination",
            status=Appointment.Status.IN_VISIT,
        )

        # 2. Create a temporary PDF file
        file_content = b"%PDF-1.4\nTest diagnostic report\n"

        uploaded_file = SimpleUploadedFile(
            "lab-report.pdf",
            file_content,
            content_type="application/pdf",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Use temporary storage for uploaded files
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):

                # 5. Submit encounter, prescriptions and file
                response = self.client.post(
                    reverse(
                        "encounter_create",
                        kwargs={"appointment_id": appointment.id},
                    ),
                    {
                        "chief_complaint": "Headache",
                        "diagnosis": "Migraine",
                        "treatment_notes": "Rest",
                        "prescriptions-TOTAL_FORMS": "2",
                        "prescriptions-INITIAL_FORMS": "0",
                        "prescriptions-MIN_NUM_FORMS": "0",
                        "prescriptions-MAX_NUM_FORMS": "1000",
                        "files-TOTAL_FORMS": "1",
                        "files-INITIAL_FORMS": "0",
                        "files-MIN_NUM_FORMS": "0",
                        "files-MAX_NUM_FORMS": "1000",
                        "files-0-title": "Blood Test Report",
                        "files-0-file_type": "LAB_REPORT",
                        "files-0-file": uploaded_file,
                    },
                )

                # 6. Check successful creation
                self.assertEqual(response.status_code, 302)

                # 7. Retrieve the created encounter
                encounter = ClinicalEncounter.objects.get(appointment=appointment)

                # 8. Retrieve the uploaded medical file
                medical_file = MedicalFile.objects.get(encounter=encounter)

                # 9. Check patient and encounter relationships
                self.assertEqual(
                    medical_file.patient,
                    self.patient,
                )
                self.assertEqual(
                    medical_file.encounter,
                    encounter,
                )

                # 10. Check that the file was stored correctly
                with medical_file.file.open("rb") as saved_file:
                    self.assertEqual(
                        saved_file.read(),
                        file_content,
                    )

    def test_completed_encounter_cannot_delete_medical_file(self):
        # 1. Create an existing medical file
        medical_file = MedicalFile.objects.create(
            patient=self.patient,
            encounter=self.encounter,
            title="Blood Test Report",
            file_type=MedicalFile.Type.LAB_REPORT,
            file="medical/test-report.pdf",
        )

        # 2. Complete the appointment
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save(update_fields=["status"])

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to delete the medical file through encounter edit
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {},
        )

        # 5. Check that editing is forbidden
        self.assertEqual(response.status_code, 403)

        # 6. Make sure the medical file still exists
        self.assertTrue(MedicalFile.objects.filter(pk=medical_file.pk).exists())

    def test_completed_encounter_cannot_add_medical_file(self):
        # 1. Complete the appointment
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save(update_fields=["status"])

        # 2. Create a test PDF file
        uploaded_file = SimpleUploadedFile(
            "new-report.pdf",
            b"%PDF-1.4\nTest report",
            content_type="application/pdf",
        )

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 4. Try to add a medical file to the completed encounter
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "Rest",
                "prescriptions-TOTAL_FORMS": "2",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
                "files-0-title": "New Lab Report",
                "files-0-file_type": "LAB_REPORT",
                "files-0-file": uploaded_file,
            },
        )

        # 5. Check that the request is forbidden
        self.assertEqual(response.status_code, 403)

        # 6. Make sure no file was added
        self.assertFalse(MedicalFile.objects.filter(encounter=self.encounter).exists())

    @patch(
        "records.views.MedicalFileFormSet.save",
        side_effect=RuntimeError("Simulated medical file save failure"),
    )
    def test_create_view_rolls_back_when_medical_file_save_fails(self, mock_save):
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            appointment_date="2026-11-24",
            time_slot="11:00",
            reason_for_visit="Medical examination",
            status=Appointment.Status.IN_VISIT,
        )

        uploaded_file = SimpleUploadedFile(
            "lab-report.pdf",
            b"%PDF-1.4\nTest report",
            content_type="application/pdf",
        )

        self.client.force_login(self.doctor_user)
        self.client.raise_request_exception = False

        response = self.client.post(
            reverse(
                "encounter_create",
                kwargs={"appointment_id": appointment.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Migraine",
                "treatment_notes": "Rest",
                "prescriptions-TOTAL_FORMS": "2",
                "prescriptions-INITIAL_FORMS": "0",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Once daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
                "files-0-title": "Blood Test",
                "files-0-file_type": "LAB_REPORT",
                "files-0-file": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 500)
        mock_save.assert_called_once()

        self.assertFalse(
            ClinicalEncounter.objects.filter(appointment=appointment).exists()
        )

        self.assertFalse(
            MedicalFile.objects.filter(
                patient=self.patient,
                title="Blood Test",
            ).exists()
        )
        self.assertFalse(Prescription.objects.exists())

    @patch(
        "records.views.MedicalFileFormSet.save",
        side_effect=RuntimeError("Simulated medical file save failure"),
    )
    def test_edit_view_rolls_back_when_medical_file_save_fails(self, mock_save):
        # 1. Create an existing prescription
        prescription = Prescription.objects.create(
            encounter=self.encounter,
            medication_name="Aspirin",
            dosage="81mg",
            frequency="Once daily",
            duration="30 days",
        )

        # 2. Save original values
        original_diagnosis = self.encounter.diagnosis
        original_frequency = prescription.frequency

        # 3. Log in as the doctor
        self.client.force_login(self.doctor_user)
        self.client.raise_request_exception = False

        # 4. Submit updated encounter and prescription data
        response = self.client.post(
            reverse(
                "encounter_edit",
                kwargs={"encounter_id": self.encounter.id},
            ),
            {
                "chief_complaint": "Headache",
                "diagnosis": "Updated diagnosis",
                "treatment_notes": "Updated notes",
                "prescriptions-TOTAL_FORMS": "1",
                "prescriptions-INITIAL_FORMS": "1",
                "prescriptions-MIN_NUM_FORMS": "0",
                "prescriptions-MAX_NUM_FORMS": "1000",
                "prescriptions-0-id": str(prescription.id),
                "prescriptions-0-medication_name": "Aspirin",
                "prescriptions-0-dosage": "81mg",
                "prescriptions-0-frequency": "Twice daily",
                "prescriptions-0-duration": "30 days",
                "prescriptions-0-instructions": "",
                "files-TOTAL_FORMS": "1",
                "files-INITIAL_FORMS": "0",
                "files-MIN_NUM_FORMS": "0",
                "files-MAX_NUM_FORMS": "1000",
            },
        )

        # 5. Verify the simulated failure
        self.assertEqual(response.status_code, 500)
        mock_save.assert_called_once()

        # 6. Reload the original records
        self.encounter.refresh_from_db()
        prescription.refresh_from_db()

        # 7. Verify that all changes were rolled back
        self.assertEqual(
            self.encounter.diagnosis,
            original_diagnosis,
        )
        self.assertEqual(
            prescription.frequency,
            original_frequency,
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VisitFlowFilesAndHistoryTests(TestCase):
    """Start-visit gate, browser completion, protected files, medical history."""

    def setUp(self):
        self.doctor_user = User.objects.create_user(
            username="flow-doctor", password="test123", role=User.Role.DOCTOR
        )
        self.other_doctor_user = User.objects.create_user(
            username="flow-other-doctor", password="test123", role=User.Role.DOCTOR
        )
        self.patient_user = User.objects.create_user(
            username="flow-patient", password="test123", role=User.Role.PATIENT
        )
        self.other_patient_user = User.objects.create_user(
            username="flow-other-patient", password="test123", role=User.Role.PATIENT
        )
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)
        self.other_doctor = DoctorProfile.objects.create(user=self.other_doctor_user)
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.other_patient = PatientProfile.objects.create(user=self.other_patient_user)

    def make_appointment(self, status, patient=None, doctor=None):
        return Appointment.objects.create(
            doctor=doctor or self.doctor,
            patient=patient or self.patient,
            appointment_date="2026-11-20",
            time_slot="10:00",
            reason_for_visit="Checkup",
            status=status,
        )

    def make_encounter(self, appointment, diagnosis="Migraine"):
        return ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=appointment.patient,
            doctor=appointment.doctor,
            chief_complaint="Headache",
            diagnosis=diagnosis,
        )

    def make_file(self, encounter=None, patient=None):
        return MedicalFile.objects.create(
            patient=patient or self.patient,
            encounter=encounter,
            title="Blood test",
            file_type=MedicalFile.Type.LAB_REPORT,
            file=SimpleUploadedFile("report.pdf", b"%PDF-1.4 data"),
        )

    # --- Start visit gate -------------------------------------------------

    def test_encounter_cannot_be_created_before_visit_is_started(self):
        appointment = self.make_appointment(Appointment.Status.APPROVED)
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_create", kwargs={"appointment_id": appointment.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_start_visit_moves_to_in_visit_and_opens_encounter_form(self):
        appointment = self.make_appointment(Appointment.Status.APPROVED)
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("start_visit", kwargs={"pk": appointment.id})
        )

        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.IN_VISIT)
        self.assertRedirects(
            response,
            reverse("encounter_create", kwargs={"appointment_id": appointment.id}),
        )

    def test_start_visit_rejects_get(self):
        appointment = self.make_appointment(Appointment.Status.APPROVED)
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("start_visit", kwargs={"pk": appointment.id})
        )

        self.assertEqual(response.status_code, 405)

    # --- Complete encounter from the browser ------------------------------

    def test_browser_complete_redirects_to_dashboard_and_locks_encounter(self):
        appointment = self.make_appointment(Appointment.Status.IN_VISIT)
        encounter = self.make_encounter(appointment)
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("complete_encounter", kwargs={"encounter_id": encounter.id}),
            HTTP_ACCEPT="text/html",
        )

        appointment.refresh_from_db()
        self.assertRedirects(response, reverse("doctor_dashboard"))
        self.assertEqual(appointment.status, Appointment.Status.COMPLETED)
        detail = self.client.get(
            reverse("encounter_detail", kwargs={"encounter_id": encounter.id})
        )
        self.assertNotContains(detail, "Complete encounter</button>")

    def test_in_visit_encounter_detail_shows_complete_button(self):
        encounter = self.make_encounter(
            self.make_appointment(Appointment.Status.IN_VISIT)
        )
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_detail", kwargs={"encounter_id": encounter.id})
        )

        self.assertContains(response, "Complete encounter</button>")

    # --- Protected file view ----------------------------------------------

    def test_patient_can_open_own_file(self):
        medical_file = self.make_file()
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse("download_file", kwargs={"pk": medical_file.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 data")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_authorized_doctor_can_open_patient_file(self):
        self.make_appointment(Appointment.Status.APPROVED)
        medical_file = self.make_file()
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("download_file", kwargs={"pk": medical_file.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_other_patient_and_unrelated_doctor_get_403(self):
        medical_file = self.make_file()
        url = reverse("download_file", kwargs={"pk": medical_file.pk})

        for user in (self.other_patient_user, self.other_doctor_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_anonymous_user_is_sent_to_login_for_file(self):
        medical_file = self.make_file()
        url = reverse("download_file", kwargs={"pk": medical_file.pk})

        response = self.client.get(url)

        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    # --- Patient medical chart (doctor) -----------------------------------

    def test_chart_is_html_for_browsers_and_json_on_request(self):
        self.make_encounter(self.make_appointment(Appointment.Status.IN_VISIT))
        self.client.force_login(self.doctor_user)
        url = reverse("patient_medical_chart", kwargs={"patient_id": self.patient.id})

        html = self.client.get(url)
        data = self.client.get(url, {"format": "json"}).json()

        self.assertTemplateUsed(html, "records/patient_chart.html")
        self.assertEqual(data["encounters"][0]["diagnosis"], "Migraine")

    # --- Medical history timeline (patient) -------------------------------

    def test_history_shows_only_own_completed_visits_newest_first(self):
        old = self.make_encounter(
            self.make_appointment(Appointment.Status.COMPLETED), diagnosis="Old flu"
        )
        new = self.make_encounter(
            self.make_appointment(
                Appointment.Status.COMPLETED, doctor=self.other_doctor
            ),
            diagnosis="Sprained ankle",
        )
        self.make_encounter(
            self.make_appointment(Appointment.Status.IN_VISIT), diagnosis="Draft visit"
        )
        self.make_encounter(
            self.make_appointment(
                Appointment.Status.COMPLETED, patient=self.other_patient
            ),
            diagnosis="Someone else",
        )
        Prescription.objects.create(
            encounter=new,
            medication_name="Ibuprofen",
            dosage="400mg",
            frequency="3x daily",
            duration="5 days",
        )
        attached = self.make_file(encounter=new)
        self.client.force_login(self.patient_user)

        response = self.client.get(reverse("medical_history"))

        self.assertEqual(list(response.context["encounters"]), [new, old])
        self.assertContains(response, "Ibuprofen")
        self.assertContains(
            response, reverse("download_file", kwargs={"pk": attached.pk})
        )
        self.assertNotContains(response, "Draft visit")
        self.assertNotContains(response, "Someone else")

    def test_history_lists_files_uploaded_outside_a_visit(self):
        loose = self.make_file()
        self.client.force_login(self.patient_user)

        response = self.client.get(reverse("medical_history"))

        self.assertEqual(list(response.context["other_files"]), [loose])

    def test_history_redirects_safely_when_profile_is_missing(self):
        missing_user = User.objects.create_user(
            "missing-history-profile",
            password="pw-test-123",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.filter(user=missing_user).delete()
        self.client.force_login(missing_user)

        response = self.client.get(reverse("medical_history"))

        self.assertRedirects(response, reverse("patient_dashboard"))

    def test_doctor_cannot_open_patient_history_page(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse("medical_history"))

        self.assertRedirects(response, reverse("doctor_dashboard"))

    # --- QA regressions ---------------------------------------------------

    def test_login_returns_to_next_url(self):
        medical_file = self.make_file()
        url = reverse("download_file", kwargs={"pk": medical_file.pk})

        response = self.client.post(
            f"{reverse('login')}?next={url}",
            {"username": "flow-patient", "password": "test123"},
        )

        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_login_ignores_offsite_next_url(self):
        response = self.client.post(
            f"{reverse('login')}?next=https://evil.example.com/",
            {"username": "flow-patient", "password": "test123"},
        )

        self.assertRedirects(
            response, reverse("home_redirect"), fetch_redirect_response=False
        )

    def test_edit_form_links_existing_file_via_protected_view_not_media(self):
        encounter = self.make_encounter(
            self.make_appointment(Appointment.Status.IN_VISIT)
        )
        medical_file = self.make_file(encounter=encounter)
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_edit", kwargs={"encounter_id": encounter.id})
        )

        self.assertContains(
            response, reverse("download_file", kwargs={"pk": medical_file.pk})
        )
        self.assertNotContains(response, "/media/")

    def test_permission_denied_uses_friendly_403_page(self):
        encounter = self.make_encounter(
            self.make_appointment(Appointment.Status.COMPLETED)
        )
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse("encounter_edit", kwargs={"encounter_id": encounter.id})
        )

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(
            response, "Completed encounters cannot be edited.", status_code=403
        )

    # --- QA round 2 -------------------------------------------------------

    def test_login_error_is_shown_once(self):
        response = self.client.post(
            reverse("login"), {"username": "flow-patient", "password": "wrong"}
        )

        self.assertEqual(response.content.decode().count("Please enter a correct"), 1)

    def test_future_visit_cannot_be_started_early(self):
        from datetime import timedelta
        from django.utils import timezone

        appointment = self.make_appointment(Appointment.Status.APPROVED)
        appointment.appointment_date = timezone.localdate() + timedelta(days=3)
        appointment.save()
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse("start_visit", kwargs={"pk": appointment.id})
        )

        appointment.refresh_from_db()
        self.assertRedirects(
            response, reverse("doctor_dashboard"), fetch_redirect_response=False
        )
        self.assertEqual(appointment.status, Appointment.Status.APPROVED)

    def test_history_and_detail_show_the_appointment_date(self):
        appointment = self.make_appointment(Appointment.Status.COMPLETED)  # 2026-11-20
        self.make_encounter(appointment)
        self.client.force_login(self.patient_user)

        response = self.client.get(reverse("medical_history"))

        self.assertContains(response, "20 Nov 2026")
