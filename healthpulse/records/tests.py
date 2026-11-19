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