from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from core.models import DoctorProfile, PatientProfile
from appointments.models import Appointment
from .models import ClinicalEncounter
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


    def test_doctor_can_complete_in_visit_encounter(self):
        # 1. Create an appointment with IN_VISIT status
        appointment = self.create_appointment(
            Appointment.Status.IN_VISIT
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # 5. Refresh appointment data from the database
        appointment.refresh_from_db()

        # 6. Check the result
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            appointment.status,
            Appointment.Status.COMPLETED
        )


    def test_another_doctor_cannot_complete_encounter(self):
        # Create an appointment for the original doctor
        appointment = self.create_appointment(
            Appointment.Status.IN_VISIT
        )

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
        other_user = User.objects.create_user(
            username="doctor2",
            password="test123"
        )
        other_user.role = User.Role.DOCTOR
        other_user.save()

        other_doctor = DoctorProfile.objects.create(
            user=other_user
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # Check that access is denied
        self.assertEqual(response.status_code, 403)

        # Check that the appointment is still in progress
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.IN_VISIT
        )

    def test_patient_cannot_complete_encounter(self):
        # Create an appointment with IN_VISIT status
        appointment = self.create_appointment(
            Appointment.Status.IN_VISIT
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # Check that access is denied
        self.assertEqual(response.status_code, 403)

        # Check that the appointment status did not change
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.IN_VISIT
        )

    def test_unauthenticated_user_cannot_complete_encounter(self):
        # Create an appointment with IN_VISIT status
        appointment = self.create_appointment(
            Appointment.Status.IN_VISIT
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # Check that the user is redirected to login
        self.assertEqual(response.status_code, 302)

        # Check that the appointment status did not change
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.IN_VISIT
        )

    def test_pending_appointment_cannot_be_completed(self):
        # 1. Create a pending appointment
        appointment = self.create_appointment(
            Appointment.Status.PENDING
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # 5. Check that access is denied
        self.assertEqual(response.status_code, 403)

        # 6. Check that the status did not change
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.PENDING
        )

    def test_completed_appointment_cannot_be_completed_again(self):
        # 1. Create an already completed appointment
        appointment = self.create_appointment(
            Appointment.Status.COMPLETED
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # 5. Check that the request is rejected
        self.assertEqual(response.status_code, 400)

        # 6. Check that the appointment remains completed
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.COMPLETED
        )
    def test_nonexistent_encounter_returns_404(self):
        # 1. Log in as the doctor
        self.client.force_login(self.doctor_user)

        # 2. Try to complete a nonexistent encounter
        response = self.client.post(
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": 99999}
            )
        )

        # 3. Check that the encounter was not found
        self.assertEqual(response.status_code, 404)


    def test_get_request_cannot_complete_encounter(self):
        # 1. Create an appointment in progress
        appointment = self.create_appointment(
            Appointment.Status.IN_VISIT
        )

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
            reverse(
                "complete_encounter",
                kwargs={"encounter_id": encounter.id}
            )
        )

        # 5. Check that GET is not allowed
        self.assertEqual(response.status_code, 405)

        # 6. Check that the appointment is unchanged
        appointment.refresh_from_db()
        self.assertEqual(
            appointment.status,
            Appointment.Status.IN_VISIT
        )
