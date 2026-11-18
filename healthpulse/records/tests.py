from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from core.models import DoctorProfile, PatientProfile
from appointments.models import Appointment
from .forms import ClinicalEncounterForm, PrescriptionFormSet
from .models import ClinicalEncounter, Prescription
from .permissions import has_relationship, require_relationship


User = get_user_model()


class DoctorPatientRelationshipTests(TestCase):

    def setUp(self):
        # Create doctor user
        self.doctor_user = User.objects.create_user(
            username="doctor1",
            password="test123"
        )
        self.doctor_user.role = User.Role.DOCTOR
        self.doctor_user.save()

        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user
        )

        # Create patient user
        self.patient_user = User.objects.create_user(
            username="patient1",
            password="test123"
        )

        self.patient = PatientProfile.objects.create(
            user=self.patient_user
        )

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

    def test_approved_appointment_allows_relationship(self):
        self.create_appointment(Appointment.Status.APPROVED)

        self.assertTrue(
            has_relationship(self.doctor, self.patient)
        )

    def test_in_visit_appointment_allows_relationship(self):
        self.create_appointment(Appointment.Status.IN_VISIT)

        self.assertTrue(
            has_relationship(self.doctor, self.patient)
        )

    def test_completed_appointment_allows_relationship(self):
        self.create_appointment(Appointment.Status.COMPLETED)

        self.assertTrue(
            has_relationship(self.doctor, self.patient)
        )

    # Rejected statuses

    def test_pending_appointment_denies_relationship(self):
        self.create_appointment(Appointment.Status.PENDING)

        self.assertFalse(
            has_relationship(self.doctor, self.patient)
        )

    def test_rejected_appointment_denies_relationship(self):
        self.create_appointment(Appointment.Status.REJECTED)

        self.assertFalse(
            has_relationship(self.doctor, self.patient)
        )

    def test_no_appointment_denies_relationship(self):
        self.assertFalse(
            has_relationship(self.doctor, self.patient)
        )

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
            reverse(
                "patient_medical_chart",
                kwargs={"patient_id": self.patient.id}
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_doctor_gets_403_for_patient_chart(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse(
                "patient_medical_chart",
                kwargs={"patient_id": self.patient.id}
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_non_doctor_gets_403_for_patient_chart(self):
        self.client.force_login(self.patient_user)

        response = self.client.get(
            reverse(
                "patient_medical_chart",
                kwargs={"patient_id": self.patient.id}
            )
        )
        self.assertEqual(response.status_code, 403)
    

    # Encounter detail view tests

    def test_authorized_doctor_can_access_encounter_detail(self):
        appointment = self.create_appointment(
            Appointment.Status.APPROVED
        )

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
            reverse(
                "encounter_detail",
                kwargs={"encounter_id": encounter.id}
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_doctor_gets_403_for_encounter_detail(self):
        appointment = self.create_appointment(
            Appointment.Status.PENDING
        )

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
            reverse(
                "encounter_detail",
                kwargs={"encounter_id": encounter.id}
            )
        )

        self.assertEqual(response.status_code, 403)

    # Doctor ownership test

    def test_doctor_cannot_access_another_doctors_encounter(self):
        appointment = self.create_appointment(
            Appointment.Status.APPROVED
        )

        encounter = ClinicalEncounter.objects.create(
            appointment=appointment,
            patient=self.patient,
            doctor=self.doctor,
            chief_complaint="Headache",
            diagnosis="Migraine",
            treatment_notes="Rest and follow-up",
        )

        other_user = User.objects.create_user(
            username="doctor2",
            password="test123"
        )
        other_user.role = User.Role.DOCTOR
        other_user.save()

        other_doctor = DoctorProfile.objects.create(
            user=other_user
        )

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
            reverse(
                "encounter_detail",
                kwargs={"encounter_id": encounter.id}
            )
        )
        self.assertEqual(response.status_code, 403)


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
            status=Appointment.Status.APPROVED,
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
            status=Appointment.Status.APPROVED,
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
            status=Appointment.Status.APPROVED,
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
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Prescription.objects.filter(pk=prescription.pk).exists()
        )

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