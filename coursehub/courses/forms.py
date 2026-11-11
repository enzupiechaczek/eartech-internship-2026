from django import forms
from django.core.exceptions import ValidationError
from .models import Course, Lesson, Module


MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024


def validate_thumbnail_size(image):
    if image and image.size > MAX_THUMBNAIL_SIZE:
        raise ValidationError("Image must be under 2 MB.")
    return image


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "subtitle",
            "category",
            "price",
            "description",
            "thumbnail",
        ]

    
    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")

        if thumbnail:
            allowed_extensions = {"jpg", "jpeg", "png"}

            extension = thumbnail.name.rsplit(".", 1)[-1].lower()

            if extension not in allowed_extensions:
                raise forms.ValidationError(
                    "Only JPG, JPEG, and PNG images are allowed."
                )

        return validate_thumbnail_size(thumbnail)



class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "notes", "video_url", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "video_url": forms.URLInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
        }
