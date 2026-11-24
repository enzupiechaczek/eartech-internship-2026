from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import DoctorProfile, PatientProfile


class RoleProfileTests(TestCase):
    def test_patient_registration_creates_patient_profile(self):
        response = self.client.post(reverse("register"), {
            "username": "new-patient",
            "first_name": "New",
            "last_name": "Patient",
            "email": "patient@example.com",
            "role": User.Role.PATIENT,
            "password1": "Strong-pass-123",
            "password2": "Strong-pass-123",
        })

        user = User.objects.get(username="new-patient")
        self.assertTrue(PatientProfile.objects.filter(user=user).exists())
        self.assertFalse(DoctorProfile.objects.filter(user=user).exists())
        self.assertRedirects(response, reverse("patient_dashboard"))

    def test_doctor_registration_creates_doctor_profile(self):
        response = self.client.post(reverse("register"), {
            "username": "new-doctor",
            "first_name": "New",
            "last_name": "Doctor",
            "email": "doctor@example.com",
            "role": User.Role.DOCTOR,
            "password1": "Strong-pass-123",
            "password2": "Strong-pass-123",
        })

        user = User.objects.get(username="new-doctor")
        self.assertTrue(DoctorProfile.objects.filter(user=user).exists())
        self.assertFalse(PatientProfile.objects.filter(user=user).exists())
        self.assertRedirects(response, reverse("doctor_dashboard"))

