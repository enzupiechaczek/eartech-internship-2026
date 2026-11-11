"""Create demo doctors, patients and appointment requests for local testing only."""
from datetime import date, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from core.models import DoctorProfile, PatientProfile, User

DEMO_PASSWORD = 'demo-pass-123'  # local development only


class Command(BaseCommand):
    help = 'Seed demo data: 2 doctors (dr_smith, dr_ali), 3 patients and a few appointment requests.'

    def handle(self, *args, **options):
        def user(username, role, first, last):
            u, created = User.objects.get_or_create(
                username=username, defaults={'role': role, 'first_name': first, 'last_name': last}
            )
            if created:
                u.set_password(DEMO_PASSWORD)
                u.save()
            return u

        smith = DoctorProfile.objects.get_or_create(user=user('dr_smith', User.Role.DOCTOR, 'John', 'Smith'))[0]
        ali = DoctorProfile.objects.get_or_create(user=user('dr_ali', User.Role.DOCTOR, 'Hassan', 'Ali'))[0]
        sara = PatientProfile.objects.get_or_create(user=user('sara', User.Role.PATIENT, 'Sara', 'Ahmed'))[0]
        omar = PatientProfile.objects.get_or_create(user=user('omar', User.Role.PATIENT, 'Omar', 'Said'))[0]
        lina = PatientProfile.objects.get_or_create(user=user('lina', User.Role.PATIENT, 'Lina', 'Khaled'))[0]

        year = timezone.now().year
        rows = [
            (sara, smith, 12, 'Chest pain since last week, worse at night', 'PENDING'),
            (omar, smith, 13, 'Follow-up on blood test results', 'PENDING'),
            (lina, smith, 14, 'Recurring headaches and dizziness', 'PENDING'),
            (lina, smith, 5, 'Annual check-up', 'APPROVED'),
            (sara, ali, 15, 'Knee pain after running', 'PENDING'),
            (omar, ali, 16, 'Skin rash', 'PENDING'),
        ]
        for patient, doctor, day, reason, status in rows:
            Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                reason_for_visit=reason,
                defaults={
                    'appointment_date': date(year, 11, day),
                    'time_slot': time(10, 0),
                    'status': status,
                },
            )
        self.stdout.write(self.style.SUCCESS('Demo data ready. Doctors: dr_smith, dr_ali (password in seed_demo.py).'))
