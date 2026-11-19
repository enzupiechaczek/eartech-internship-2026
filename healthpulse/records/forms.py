from django import forms
from .models import ClinicalEncounter

class EncounterForm(forms.ModelForm):
    class Meta:
        model = ClinicalEncounter
        fields = ["chief_complaint", "diagnosis", "treatment_notes"]