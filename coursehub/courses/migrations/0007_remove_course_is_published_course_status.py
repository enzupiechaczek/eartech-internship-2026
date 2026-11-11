from django.db import migrations, models


def copy_published(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.filter(is_published=True).update(status="PUBLISHED")


def copy_back(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    Course.objects.filter(status="PUBLISHED").update(is_published=True)


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_course_students'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='status',
            field=models.CharField(
                choices=[('DRAFT', 'Draft'), ('PUBLISHED', 'Published')],
                default='DRAFT',
                max_length=10,
            ),
        ),
        migrations.RunPython(copy_published, copy_back),
        migrations.RemoveField(
            model_name='course',
            name='is_published',
        ),
    ]