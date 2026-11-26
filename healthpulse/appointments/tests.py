from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import DoctorProfile, PatientProfile

from .models import Appointment


class AppointmentStatusTransitionTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            'status-doctor',
            password='pw-test-123',
            role=User.Role.DOCTOR,
        )
        self.patient_user = User.objects.create_user(
            'status-patient',
            password='pw-test-123',
            role=User.Role.PATIENT,
        )
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)
        self.patient = PatientProfile.objects.create(user=self.patient_user)

    def create_appointment(self, status=None):
        appointment_fields = {
            'patient': self.patient,
            'doctor': self.doctor,
            'appointment_date': timezone.localdate() + timedelta(days=1),
            'time_slot': time(10, 0),
            'reason_for_visit': 'Status transition test',
        }
        if status is not None:
            appointment_fields['status'] = status
        return Appointment.objects.create(**appointment_fields)

    def update_status(self, appointment, status):
        self.client.force_login(self.doctor_user)
        return self.client.post(
            reverse('update_appointment_status', kwargs={'pk': appointment.pk}),
            data={'status': status},
            content_type='application/json',
        )

    def test_new_appointment_defaults_to_pending(self):
        appointment = self.create_appointment()

        self.assertEqual(appointment.status, Appointment.Status.PENDING)

    def test_pending_appointment_can_be_approved_and_status_is_persisted(self):
        appointment = self.create_appointment()

        response = self.update_status(
            appointment,
            Appointment.Status.APPROVED,
        )

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.APPROVED)

    def test_pending_appointment_can_be_rejected_and_status_is_persisted(self):
        appointment = self.create_appointment()

        response = self.update_status(
            appointment,
            Appointment.Status.REJECTED,
        )

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.REJECTED)

    def test_pending_appointment_cannot_transition_to_in_visit(self):
        appointment = self.create_appointment()

        response = self.update_status(
            appointment,
            Appointment.Status.IN_VISIT,
        )

        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)

    def test_non_pending_appointment_cannot_transition_to_rejected(self):
        appointment = self.create_appointment(Appointment.Status.APPROVED)

        response = self.update_status(
            appointment,
            Appointment.Status.REJECTED,
        )

        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.APPROVED)


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


class BookingAndExpiryTests(TestCase):
    def setUp(self):
        from core.models import DoctorProfile, PatientProfile

        self.doctor_user = User.objects.create_user('exp-doc', password='pw-test-123', role=User.Role.DOCTOR)
        self.patient_user = User.objects.create_user('exp-pat', password='pw-test-123', role=User.Role.PATIENT)
        self.doctor = DoctorProfile.objects.create(user=self.doctor_user)
        self.patient = PatientProfile.objects.create(user=self.patient_user)

    def test_booking_shows_confirmation_and_blocks_past_dates_in_picker(self):
        self.client.force_login(self.patient_user)
        url = reverse('book_appointment', kwargs={'doctor_id': self.doctor.pk})

        page = self.client.get(url)
        response = self.client.post(url, {
            'appointment_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
            'time_slot': '10:00',
            'reason_for_visit': 'Check-up',
        }, follow=True)

        self.assertContains(page, f'min="{timezone.localdate().isoformat()}"')
        self.assertContains(response, 'Appointment requested for')

    def test_patient_without_profile_is_redirected_safely(self):
        user = User.objects.create_user(
            "missing-profile",
            password="pw-test-123",
            role=User.Role.PATIENT,
        )
        PatientProfile.objects.filter(user=user).delete()
        self.client.force_login(user)

        url = reverse(
            "book_appointment",
            kwargs={"doctor_id": self.doctor.pk},
        )
        response = self.client.post(url, {
            "appointment_date": (
                timezone.localdate() + timedelta(days=2)
            ).isoformat(),
            "time_slot": "10:00",
            "reason_for_visit": "Check-up",
        })

        self.assertRedirects(response, reverse("patient_dashboard"))
        self.assertFalse(Appointment.objects.filter(patient__user=user).exists())

    def test_past_pending_request_is_expired_and_cannot_be_approved(self):
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            appointment_date=timezone.localdate() - timedelta(days=1),
            time_slot='10:00', reason_for_visit='Old request',
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse('update_appointment_status', kwargs={'pk': appt.pk}),
            data='{"status": "APPROVED"}', content_type='application/json',
        )

        appt.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(appt.status, Appointment.Status.PENDING)
        self.assertEqual(appt.status_label, 'Expired')
