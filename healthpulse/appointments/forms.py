
from datetime import date

from django import forms

from .models import Appointment


class BookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            "appointment_date",
            "time_slot",
            "reason_for_visit",
        ]
        widgets = {
            "appointment_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "time_slot": forms.TimeInput(
                attrs={"type": "time"}
            ),
            "reason_for_visit": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def clean_appointment_date(self):
        appointment_date = self.cleaned_data["appointment_date"]

        if appointment_date < date.today():
            raise forms.ValidationError(
                "Please choose a future date."
            )

        return appointment_date
