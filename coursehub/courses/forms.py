
from django import forms
from django.core.exceptions import ValidationError

from .models import Course


MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024


def validate_thumbnail_size(image):
    if image and image.size > MAX_THUMBNAIL_SIZE:
        raise ValidationError("Image must be under 2 MB.")
    return image


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "price", "thumbnail", "is_published"]

    def clean_thumbnail(self):
        return validate_thumbnail_size(
            self.cleaned_data.get("thumbnail")
        )
