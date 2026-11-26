from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import DoctorProfile, PatientProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo doctor and patient accounts and profiles"

    def handle(self, *args, **options):
        password = "Demo@123"

        doctors = [
            ("dr.smith", "John", "Cardiology", "Downtown Clinic"),
            ("dr.ali", "Ali", "General Medicine", "Main Clinic"),
        ]

        for username, first_name, specialty, clinic_branch in doctors:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": User.Role.DOCTOR,
                    "first_name": first_name,
                },
            )
            if created or not user.check_password(password):
                user.role = User.Role.DOCTOR
                user.first_name = first_name
                user.set_password(password)
                user.save()

            DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "specialty": specialty,
                    "clinic_branch": clinic_branch,
                },
            )

        patients = [
            ("patient1", "Patient One"),
            ("patient2", "Patient Two"),
        ]

        for username, first_name in patients:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": User.Role.PATIENT,
                    "first_name": first_name,
                },
            )
            if created or not user.check_password(password):
                user.role = User.Role.PATIENT
                user.first_name = first_name
                user.set_password(password)
                user.save()

            PatientProfile.objects.get_or_create(user=user)

        self.stdout.write(self.style.SUCCESS("Demo data ready"))