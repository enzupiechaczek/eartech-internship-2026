from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .models import Course, Lesson, Module


MAX_THUMBNAIL_SIZE = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def validate_thumbnail_size(image):
    if isinstance(image, UploadedFile) and image.size > MAX_THUMBNAIL_SIZE:
        raise ValidationError("Thumbnail must be 2MB or smaller.")
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

        if isinstance(thumbnail, UploadedFile):
            extension = thumbnail.name.rsplit(".", 1)[-1].lower()

            if extension not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    "Only JPG, JPEG, PNG, and WEBP images are allowed."
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
