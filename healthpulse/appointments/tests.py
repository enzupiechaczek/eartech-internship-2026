from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import DoctorProfile, PatientProfile, User

from .models import Appointment


class PendingRequestsTests(TestCase):
    def setUp(self):
        self.smith = User.objects.create_user('smith', password='pw-test-123', role=User.Role.DOCTOR)
        self.ali = User.objects.create_user('ali', password='pw-test-123', role=User.Role.DOCTOR)
        self.sara = User.objects.create_user(
            'sara', password='pw-test-123', role=User.Role.PATIENT, first_name='Sara', last_name='Ahmed'
        )
        self.dr_smith = DoctorProfile.objects.create(user=self.smith)
        self.dr_ali = DoctorProfile.objects.create(user=self.ali)
        self.patient = PatientProfile.objects.create(user=self.sara)
        self.url = reverse('pending_requests')

    def make(self, doctor, reason, status=Appointment.Status.PENDING):
        return Appointment.objects.create(
            patient=self.patient,
            doctor=doctor,
            appointment_date=timezone.localdate() + timedelta(days=1),
            time_slot=time(10, 0),
            reason_for_visit=reason,
            status=status,
        )

    def test_doctor_sees_only_own_pending_requests(self):
        mine = self.make(self.dr_smith, 'Chest pain')
        self.make(self.dr_smith, 'Old approved visit', status=Appointment.Status.APPROVED)
        self.make(self.dr_ali, 'Request for Dr Ali')

        self.client.force_login(self.smith)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['appts']), [mine])
        self.assertContains(response, 'Sara Ahmed')
        self.assertContains(response, 'Chest pain')
        self.assertContains(response, 'data-action="APPROVED"')
        self.assertContains(response, 'data-action="REJECTED"')
        self.assertNotContains(response, 'Request for Dr Ali')
        self.assertNotContains(response, 'Old approved visit')

    def test_patient_cannot_open_page(self):
        self.client.force_login(self.sara)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('patient_dashboard'))

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
