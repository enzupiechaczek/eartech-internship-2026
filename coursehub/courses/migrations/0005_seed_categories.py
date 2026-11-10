from django.db import migrations

CATEGORIES = [
    "Web Development",
    "Cybersecurity",
    "AI",
    "Data",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("courses", "Category")
    for name in CATEGORIES:
        Category.objects.get_or_create(name=name)


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("courses", "Category")
    Category.objects.filter(name__in=CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0004_category_and_course_fields"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
