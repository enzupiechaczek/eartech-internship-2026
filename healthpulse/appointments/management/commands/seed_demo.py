"""Create demo doctors, patients and appointment requests for local testing only."""
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from accounts.models import User
from core.models import DoctorProfile, PatientProfile

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

        def doctor(username, first, last, specialty, clinic, bio, qualifications):
            profile = DoctorProfile.objects.get_or_create(
                user=user(username, User.Role.DOCTOR, first, last)
            )[0]
            # Fill only blank fields so local edits are never overwritten.
            for field, value in (
                ("specialty", specialty),
                ("clinic_branch", clinic),
                ("bio", bio),
                ("qualifications", qualifications),
            ):
                if not getattr(profile, field):
                    setattr(profile, field, value)
            profile.save()
            return profile

        smith = doctor(
            'dr_smith', 'John', 'Smith', 'Cardiology', 'Downtown Clinic',
            'Cardiologist focused on preventive heart care and long-term follow-up.',
            'MD, Board Certified in Cardiology',
        )
        ali = doctor(
            'dr_ali', 'Hassan', 'Ali', 'Orthopedics', 'Northside Clinic',
            'Orthopedic doctor treating sports injuries and joint pain.',
            'MD, Fellowship in Sports Medicine',
        )
        sara = PatientProfile.objects.get_or_create(user=user('sara', User.Role.PATIENT, 'Sara', 'Ahmed'))[0]
        omar = PatientProfile.objects.get_or_create(user=user('omar', User.Role.PATIENT, 'Omar', 'Said'))[0]
        lina = PatientProfile.objects.get_or_create(user=user('lina', User.Role.PATIENT, 'Lina', 'Khaled'))[0]

        today = timezone.localdate()
        rows = [
            # (patient, doctor, days from today, reason, status)
            (sara, smith, 2, 'Chest pain since last week, worse at night', 'PENDING'),
            (omar, smith, 3, 'Follow-up on blood test results', 'PENDING'),
            (lina, smith, 4, 'Recurring headaches and dizziness', 'PENDING'),
            (lina, smith, 0, 'Annual check-up', 'APPROVED'),
            (sara, ali, 5, 'Knee pain after running', 'PENDING'),
            (omar, ali, 6, 'Skin rash', 'PENDING'),
        ]
        for patient, doctor, days, reason, status in rows:
            Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                reason_for_visit=reason,
                defaults={
                    'appointment_date': today + timedelta(days=days),
                    'time_slot': time(10, 0),
                    'status': status,
                },
            )
        self.stdout.write(self.style.SUCCESS('Demo data ready. Doctors: dr_smith, dr_ali (password in seed_demo.py).'))
