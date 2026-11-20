from django.contrib import admin
from .models import ClinicalEncounter, Prescription

admin.site.register(ClinicalEncounter)
admin.site.register(Prescription)

# Register your models here.
