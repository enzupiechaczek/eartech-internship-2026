from django.db import migrations


def create_missing_role_profiles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    PatientProfile = apps.get_model("core", "PatientProfile")
    DoctorProfile = apps.get_model("core", "DoctorProfile")

    for user in User.objects.filter(role="PATIENT").iterator():
        PatientProfile.objects.get_or_create(user_id=user.pk)

    for user in User.objects.filter(role="DOCTOR").iterator():
        DoctorProfile.objects.get_or_create(user_id=user.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("core", "0004_delete_user"),
    ]

    operations = [
        migrations.RunPython(
            create_missing_role_profiles,
            migrations.RunPython.noop,
        ),
    ]
