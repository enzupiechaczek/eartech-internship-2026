
from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet

from .models import ClinicalEncounter, Prescription, MedicalFile


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

PrescriptionInlineFormSet = PrescriptionFormSet


class MedicalFileForm(forms.ModelForm):
    class Meta:
        model = MedicalFile
        fields = ["title", "file_type", "file"]


class BaseMedicalFileFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        medical_file = super().save_new(form, commit=False)

        medical_file.patient = self.instance.patient

        if commit:
            medical_file.save()

        return medical_file


MedicalFileFormSet = inlineformset_factory(
    ClinicalEncounter,
    MedicalFile,
    form=MedicalFileForm,
    formset=BaseMedicalFileFormSet,
    fields=["title", "file_type", "file"],
    extra=1,
    can_delete=True,
)
