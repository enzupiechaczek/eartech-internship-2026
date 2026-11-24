from django.contrib import admin

from .models import ClinicalEncounter, MedicalFile, Prescription


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0


@admin.register(ClinicalEncounter)
class ClinicalEncounterAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "visit_date", "diagnosis")
    list_filter = ("doctor", "visit_date")
    inlines = [PrescriptionInline]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("medication_name", "dosage", "frequency", "encounter")


@admin.register(MedicalFile)
class MedicalFileAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "patient", "encounter", "uploaded_at")
    list_filter = ("file_type",)
