from django import forms
from django.forms import inlineformset_factory

from .models import ClinicalEncounter, Prescription


class ClinicalEncounterForm(forms.ModelForm):
    class Meta:
        model = ClinicalEncounter
        fields = ["chief_complaint", "diagnosis", "treatment_notes"]


EncounterForm = ClinicalEncounterForm


PrescriptionFormSet = inlineformset_factory(
    ClinicalEncounter,
    Prescription,
    fields=[
        "medication_name",
        "dosage",
        "frequency",
        "duration",
        "instructions",
    ],
    extra=2,
    can_delete=True,
)

# Descriptive alias for callers that prefer an explicit inline formset name.
PrescriptionInlineFormSet = PrescriptionFormSet
