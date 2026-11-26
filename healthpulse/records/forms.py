from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet

from .models import ClinicalEncounter, Prescription, MedicalFile


class ClinicalEncounterForm(forms.ModelForm):
    class Meta:
        model = ClinicalEncounter
        fields = ["chief_complaint", "diagnosis", "treatment_notes"]
        widgets = {
            "chief_complaint": forms.Textarea(attrs={"rows": 3}),
            "treatment_notes": forms.Textarea(attrs={"rows": 3}),
        }


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
    widgets={
        "instructions": forms.Textarea(attrs={"rows": 2}),
    },
    extra=1,
    can_delete=True,
)

PrescriptionInlineFormSet = PrescriptionFormSet


class MedicalFileForm(forms.ModelForm):
    class Meta:
        model = MedicalFile
        fields = ["title", "file_type", "file"]
        # Plain FileInput: ClearableFileInput renders a "Currently: <link>"
        # pointing at /media/, which is intentionally not served (and leaks
        # the storage path). Existing files are linked via the protected view.
        widgets = {
            "file": forms.FileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep the blank choice (an untouched extra row must stay "empty"),
        # but give it a readable label instead of Django's dashes.
        self.fields["file_type"].choices = [("", "Choose a type")] + list(
            MedicalFile.Type.choices
        )


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
